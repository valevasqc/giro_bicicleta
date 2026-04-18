#include <RadioLib.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// --- OLED (Heltec LoRa32 V4) ---
// RST=-1: SSD1306 resets on power-up; software RST pin not needed and
// may conflict with VEXT power control on the V4.
// TODO: Screen is blank after flash. Heltec V4 requires VEXT (pin 36?) to be
// driven LOW before Wire.begin() to power the OLED. Add:
//   pinMode(36, OUTPUT); digitalWrite(36, LOW); delay(50);
// before Wire.begin() and verify OLED_SDA/SCL pins match your board variant.
#define OLED_SDA 17
#define OLED_SCL 18
#define OLED_RST -1
Adafruit_SSD1306 display(128, 64, &Wire, OLED_RST);

// --- LoRa (SX1262) ---
SX1262 radio = new Module(8, 14, 12, 13);
bool radioOk = false;
volatile bool receivedFlag = false;

String lastTx = "";
String lastRx = "";
float lastRssi = 0;
float lastSnr  = 0;

void IRAM_ATTR setFlag(void) {
  receivedFlag = true;
}

// Truncate long strings with a trailing ~ so they fit on screen.
String trunc(const String& s, int maxLen) {
  if ((int)s.length() <= maxLen) return s;
  return s.substring(0, maxLen - 1) + "~";
}

void updateDisplay(const String& status) {
  display.clearDisplay();
  display.setTextSize(1);       // 6x8 px per char → 21 cols, 8 rows
  display.setTextColor(SSD1306_WHITE);

  display.setCursor(0, 0);
  display.println(trunc(status, 21));

  display.setCursor(0, 16);
  display.print("TX:");
  display.println(trunc(lastTx, 18));

  display.setCursor(0, 32);
  display.print("RX:");
  display.println(trunc(lastRx, 18));

  display.setCursor(0, 48);
  display.print("RSSI:");
  display.print((int)lastRssi);
  display.print("dBm SNR:");
  display.print((int)lastSnr);
  display.print("dB");

  display.display();
}

void setup() {
  Serial.begin(115200);
  delay(1500);

  Wire.begin(OLED_SDA, OLED_SCL);
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("ERROR|OLED|init failed");
  } else {
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.println("Initializing...");
    display.display();
  }

  SPI.begin(9, 11, 10, 8);
  int state = radio.begin(915.0, 125.0, 9, 7, 0x12, 22);
  if (state == RADIOLIB_ERR_NONE) {
    radio.setDio2AsRfSwitch(true);
    radio.setPacketReceivedAction(setFlag);
    radioOk = true;
    radio.startReceive();
    Serial.println("READY");
    Serial.println("# 915MHz BW=125 SF=9 CR=7 sync=0x12 pwr=22dBm");
    updateDisplay("READY 915MHz SF9");
  } else {
    Serial.print("ERROR|INIT|");
    Serial.println(state);
    updateDisplay("ERR INIT " + String(state));
  }
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() > 0 && radioOk) {
      lastTx = line;
      Serial.print("# TX: "); Serial.println(line);
      updateDisplay("Sending...");

      radio.clearPacketReceivedAction();
      int state = radio.transmit(line);

      if (state == RADIOLIB_ERR_NONE) {
        Serial.println("# TX ok");
        updateDisplay("TX ok");
      } else {
        Serial.print("TX result: "); Serial.println(state);
        updateDisplay("TX ERR " + String(state));
      }

      radio.setPacketReceivedAction(setFlag);
      radio.startReceive();
    }
  }

  if (receivedFlag) {
    receivedFlag = false;
    String msg;
    int state = radio.readData(msg);
    // Read signal quality before startReceive() resets the registers.
    float rssi = radio.getRSSI();
    float snr  = radio.getSNR();
    // Re-enter RX mode ASAP — before Serial prints or display update —
    // so a back-to-back packet isn't missed while we're busy.
    radio.startReceive();
    if (state == RADIOLIB_ERR_NONE) {
      lastRx   = msg;
      lastRssi = rssi;
      lastSnr  = snr;
      Serial.println(msg);
      Serial.print("# RX rssi=");
      Serial.print(lastRssi);
      Serial.print("dBm snr=");
      Serial.print(lastSnr);
      Serial.println("dB");
      updateDisplay("RX ok");
    } else {
      Serial.print("RX ERR: "); Serial.println(state);
      updateDisplay("RX ERR " + String(state));
    }
  }
}
