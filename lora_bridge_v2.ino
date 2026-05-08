// lora_bridge_heltec_v2.ino — Heltec WiFi LoRa 32 V2 (SX1276 + OLED) serial bridge.
//   - PA_BOOST forced via setOutputPower(20, false). Heltec V2 only wires PA_BOOST.
// Serial protocol identical to V4 bridge: READY / ERROR|INIT|<code> / raw payload / # comments.

#include <RadioLib.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// --- OLED (Heltec LoRa32 V2) ---
#define OLED_SDA 4
#define OLED_SCL 15
#define OLED_RST 16
#define VEXT     21

// --- LoRa SX1276 ---
#define LORA_SCK  5
#define LORA_MISO 19
#define LORA_MOSI 27
#define LORA_NSS  18
#define LORA_DIO0 26
#define LORA_RST  14
#define LORA_DIO1 35

Adafruit_SSD1306 display(128, 64, &Wire, OLED_RST);
bool displayOk = false;

// SX1276: Module(cs, irq, rst, gpio)
SX1276 radio = new Module(LORA_NSS, LORA_DIO0, LORA_RST, LORA_DIO1);
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

  // Power OLED rail
  VextON();
  delay(200);

  // V2 needs an explicit OLED reset pulse
  pinMode(OLED_RST, OUTPUT);
  digitalWrite(OLED_RST, LOW);  delay(50);
  digitalWrite(OLED_RST, HIGH); delay(50);

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

  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_NSS);

  // 915 MHz / BW125 / SF9 / CR4/7 / sync 0x12 / 17 dBm placeholder / preamble 8 / gain auto
  int state = radio.begin(915.0, 125.0, 9, 7, 0x12, 17, 8, 0);
  if (state == RADIOLIB_ERR_NONE) {
    // Force PA_BOOST output (false = useRfo=false → PA_BOOST). V2 only wires PA_BOOST.
    radio.setOutputPower(20, false);
    // RX gain stays at AGC default — adapts across distance.
    radio.setPacketReceivedAction(setFlag);
    radioOk = true;
    radio.startReceive();
    Serial.println("READY");
    Serial.println("# 915MHz BW=125 SF=9 CR=7 sync=0x12 pwr=20dBm PA_BOOST");
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
