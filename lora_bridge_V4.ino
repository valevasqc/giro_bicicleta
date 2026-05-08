// lora_bridge_heltec.ino — Heltec WiFi LoRa 32 V4 (SX1262 + GC1109 FEM) serial bridge.
// Long-range build:
//   - TCXO 1.8V (Heltec hardware; RadioLib default 1.6V loses 10-30 dB).
//   - DCDC regulator (LDO undervolts the PA on TX peaks).
//   - GC1109 FEM enabled: CSD=GPIO2 HIGH always, CTX via DIO2, CPS=GPIO46
//     HIGH only during TX (GPIO46 is a strapping pin, must float at boot).
// Serial protocol unchanged: READY / ERROR|INIT|<code> / raw payload / # comments.

#include <RadioLib.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// --- OLED (Heltec LoRa32 V4) ---
#define OLED_SDA 17
#define OLED_SCL 18
#define OLED_RST 21
#define VEXT 36

// --- LoRa SX1262 ---
#define LORA_NSS  8
#define LORA_DIO1 14
#define LORA_RST  12
#define LORA_BUSY 13
#define LORA_SCK  9
#define LORA_MISO 11
#define LORA_MOSI 10

// --- V4.2 GC1109 FEM ---
#define FEM_CSD 2    // FEM enable — HIGH always
#define FEM_CPS 46   // TX bypass — HIGH only during TX (strapping pin!)

Adafruit_SSD1306 display(128, 64, &Wire, OLED_RST);
bool displayOk = false;

SX1262 radio = new Module(LORA_NSS, LORA_DIO1, LORA_RST, LORA_BUSY);
bool radioOk = false;
volatile bool receivedFlag = false;

String lastTx = "";
String lastRx = "";
float lastRssi = 0;
float lastSnr  = 0;

void IRAM_ATTR setFlag(void) {
  receivedFlag = true;
}

void VextON() {
  pinMode(VEXT, OUTPUT);
  digitalWrite(VEXT, LOW);
}

// FEM-aware transmit. GPIO46 is a strapping pin — only OUTPUT during TX.
int transmitFEM(String& pkt) {
  pinMode(FEM_CPS, OUTPUT);
  digitalWrite(FEM_CPS, HIGH);
  int state = radio.transmit(pkt);
  digitalWrite(FEM_CPS, LOW);
  pinMode(FEM_CPS, INPUT);
  return state;
}

String trunc(const String& s, int maxLen) {
  if ((int)s.length() <= maxLen) return s;
  return s.substring(0, maxLen - 1) + "~";
}

void updateDisplay(const String& status) {
  if (!displayOk) return;
  display.clearDisplay();
  display.setTextSize(1);
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
  display.print(" SNR:");
  display.print((int)lastSnr);

  display.display();
}

void setup() {
  Serial.begin(115200);
  delay(1500);

  // Power the OLED first
  VextON();
  delay(100);

  Wire.begin(OLED_SDA, OLED_SCL);
  Wire.setTimeOut(50);
  delay(50);

  // Probe before display.begin() to avoid hang on missing/dead OLED.
  Wire.beginTransmission(0x3C);
  uint8_t probe = Wire.endTransmission();
  if (probe != 0) {
    Serial.print("# OLED not found (probe=");
    Serial.print(probe);
    Serial.println(") - display disabled");
  } else if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("ERROR|OLED|init failed");
  } else {
    displayOk = true;
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.println("Initializing...");
    display.display();
  }

  // FEM enable BEFORE radio init. CPS stays as INPUT (default) until first TX.
  pinMode(FEM_CSD, OUTPUT);
  digitalWrite(FEM_CSD, HIGH);
  Serial.println("# FEM GC1109 enabled (GPIO2=HIGH)");

  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_NSS);

  // 915 MHz / BW125 / SF9 / CR4/7 / sync 0x12 / 22 dBm / preamble 8 / TCXO 1.8V / DCDC
  int state = radio.begin(915.0, 125.0, 9, 7, 0x12, 22, 8, 1.8, false);
  if (state == RADIOLIB_ERR_NONE) {
    radio.setDio2AsRfSwitch(true);   // FEM CTX line
    // NO setRxBoostedGainMode on V4 — FEM has its own LNA.
    radio.setPacketReceivedAction(setFlag);
    radioOk = true;
    radio.startReceive();
    Serial.println("READY");
    Serial.println("# 915MHz BW=125 SF=9 CR=7 sync=0x12 pwr=22dBm FEM=on");
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
      int state = transmitFEM(line);

      radio.setPacketReceivedAction(setFlag);
      radio.startReceive();

      if (state == RADIOLIB_ERR_NONE) {
        Serial.println("# TX ok");
        updateDisplay("TX ok");
      } else {
        Serial.print("TX result: "); Serial.println(state);
        updateDisplay("TX ERR " + String(state));
      }
    }
  }

  if (receivedFlag) {
    receivedFlag = false;
    String msg;
    int state = radio.readData(msg);
    float rssi = radio.getRSSI();
    float snr  = radio.getSNR();
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
