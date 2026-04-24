#include <RadioLib.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// --- OLED (Heltec LoRa32 V4) ---
#define OLED_SDA 17
#define OLED_SCL 18
#define OLED_RST 21
#define VEXT 36

Adafruit_SSD1306 display(128, 64, &Wire, OLED_RST);
bool displayOk = false;

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

  // Power the OLED first
  VextON();
  delay(100);

  Wire.begin(OLED_SDA, OLED_SCL);
  Wire.setTimeOut(50);  // don't hang forever if OLED isn't present
  delay(50);

  // Probe for the OLED before calling display.begin(). A dead/broken panel
  // on a board where VextON() just powered it up can hang display.begin()
  // indefinitely despite Wire.setTimeOut — it does many transactions and
  // the Adafruit library doesn't check return values. One beginTransmission
  // is bounded and returns non-zero fast if the device doesn't ACK 0x3C.
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

      // Re-enter RX mode BEFORE the display update — updateDisplay() does
      // I2C writes that can be slow (or hang on a missing OLED), and any
      // reply packet that arrives during that window would be lost.
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