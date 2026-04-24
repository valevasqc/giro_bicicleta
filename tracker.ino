#include "Arduino.h"
#include "HT_st7735.h"
#include "HT_TinyGPS++.h"
#include <RadioLib.h>
#include <SPI.h>
#include <HardwareSerial.h>
#include <time.h>

#ifndef Vext
#define Vext 3
#endif

// ----- Screen -----
HT_st7735 st7735;

// ----- GPS -----
TinyGPSPlus gps;
HardwareSerial gpsSerial(1);

#define GPS_BAUD   115200
#define GPS_RX_PIN 33
#define GPS_TX_PIN 34

// ----- LoRa -----
SX1262 radio = new Module(8, 14, 12, 13);
bool radioOk = false;

#define RF_FREQUENCY      915.0
#define LORA_BANDWIDTH    125.0
#define LORA_SF           9
#define LORA_CODINGRATE   7
#define LORA_SYNC_WORD    0x12
#define LORA_TX_POWER     22
#define TX_INTERVAL_MS    30000

#define BIKE_ID "B1"

unsigned long lastTx = 0;
unsigned long txCount = 0;
String lastStatus = "boot";
String lastMsg = "";
double lastLat = 0.0;
double lastLon = 0.0;
int lastSats = 0;
bool hasFix = false;

void drawScreen() {
  st7735.st7735_fill_screen(ST7735_BLACK);

  st7735.st7735_write_str(0, 0, "Tracker");

  String line1 = String("LoRa: ") + (radioOk ? "OK" : "ERR");
  st7735.st7735_write_str(0, 18, line1);

  String line3 = String("Sat: ") + String(lastSats);
  st7735.st7735_write_str(0, 36, line3);

  String latStr = "Lat:" + String(lastLat, 4);
  st7735.st7735_write_str(0, 54, latStr);

  String lonStr = "Lon:" + String(lastLon, 4);
  st7735.st7735_write_str(0, 72, lonStr);

  String txStr = "TX#:" + String(txCount);
  st7735.st7735_write_str(0, 90, txStr);

  st7735.st7735_write_str(0, 108, lastStatus);
}

void setupLoRa() {
  SPI.begin(9, 11, 10, 8);

  int state = radio.begin(
    RF_FREQUENCY,
    LORA_BANDWIDTH,
    LORA_SF,
    LORA_CODINGRATE,
    LORA_SYNC_WORD,
    LORA_TX_POWER
  );

  if (state == RADIOLIB_ERR_NONE) {
    radio.setDio2AsRfSwitch(true);
    radioOk = true;
    Serial.println("[lora] init OK");
    lastStatus = "LoRa OK";
  } else {
    radioOk = false;
    Serial.print("[lora] init FAIL: ");
    Serial.println(state);
    lastStatus = "LoRa ERR " + String(state);
  }
}

void feedGPS(unsigned long ms) {
  unsigned long start = millis();
  while (millis() - start < ms) {
    while (gpsSerial.available()) {
      gps.encode(gpsSerial.read());
    }
    delay(5);
  }
}

unsigned long buildUnixTime() {
  if (!gps.date.isValid() || !gps.time.isValid()) return 0;

  struct tm t = {};
  t.tm_year = gps.date.year() - 1900;
  t.tm_mon  = gps.date.month() - 1;
  t.tm_mday = gps.date.day();
  t.tm_hour = gps.time.hour();
  t.tm_min  = gps.time.minute();
  t.tm_sec  = gps.time.second();

  setenv("TZ", "UTC0", 1);
  tzset();

  return (unsigned long)mktime(&t);
}

void sendGpsPacket() {
  feedGPS(2000);

  hasFix = gps.location.isValid();
  lastSats = gps.satellites.isValid() ? gps.satellites.value() : 0;

  char msg[96];

  if (hasFix) {
    lastLat = gps.location.lat();
    lastLon = gps.location.lng();
    unsigned long ts = buildUnixTime();

    snprintf(
      msg,
      sizeof(msg),
      "GPS|%s|%lu|%.6f|%.6f",
      BIKE_ID,
      ts,
      lastLat,
      lastLon
    );
  } else {
    lastLat = 0.0;
    lastLon = 0.0;

    snprintf(
      msg,
      sizeof(msg),
      "GPS|%s|0|0.000000|0.000000",
      BIKE_ID
    );
  }

  lastMsg = String(msg);

  Serial.print("[lora] TX -> ");
  Serial.println(lastMsg);

  if (!radioOk) {
    lastStatus = "No LoRa";
    drawScreen();
    return;
  }

  int state = radio.transmit(msg);

  if (state == RADIOLIB_ERR_NONE) {
    txCount++;
    lastStatus = "TX ok";
    Serial.println("[lora] TX OK");
  } else {
    lastStatus = "TX ERR " + String(state);
    Serial.print("[lora] TX FAIL: ");
    Serial.println(state);
  }

  Serial.printf(
    "[gps] fix=%s sats=%d lat=%.6f lon=%.6f\n",
    hasFix ? "YES" : "NO",
    lastSats,
    lastLat,
    lastLon
  );

  drawScreen();
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n[boot] Wireless Tracker GPS LoRa sender");

  st7735.st7735_init();
  st7735.st7735_fill_screen(ST7735_BLACK);
  st7735.st7735_write_str(0, 0, "Booting...");

  pinMode(Vext, OUTPUT);
  digitalWrite(Vext, HIGH);
  delay(500);

  gpsSerial.begin(GPS_BAUD, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
  Serial.println("[gps] UART started RX=33 TX=34");

  setupLoRa();
  drawScreen();

  lastTx = millis() - TX_INTERVAL_MS + 5000;
}

void loop() {
  while (gpsSerial.available()) {
    gps.encode(gpsSerial.read());
  }

  static unsigned long lastDebug = 0;
  if (millis() - lastDebug >= 2000) {
    lastDebug = millis();

    hasFix = gps.location.isValid();
    lastSats = gps.satellites.isValid() ? gps.satellites.value() : 0;
    if (hasFix) {
      lastLat = gps.location.lat();
      lastLon = gps.location.lng();
    }

    Serial.printf(
      "[gps] chars=%lu valid=%s sats=%d lat=%.6f lon=%.6f\n",
      gps.charsProcessed(),
      hasFix ? "YES" : "NO",
      lastSats,
      hasFix ? lastLat : 0.0,
      hasFix ? lastLon : 0.0
    );

    drawScreen();
  }

  if (millis() - lastTx >= TX_INTERVAL_MS) {
    lastTx = millis();
    sendGpsPacket();
  }
}