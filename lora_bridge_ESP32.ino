#include <RadioLib.h>

// SX1276 wiring:
// NSS/CS = 5, DIO0 = 26, RST = 14, DIO1 = 33
SX1276 radio = new Module(5, 26, 14, 33);

bool radioOk = false;
volatile bool receivedFlag = false;

String lastTx = "";
String lastRx = "";

void IRAM_ATTR setFlag(void) {
  receivedFlag = true;
}

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.println("# ESP32 + SX1276 LoRa bridge starting");

  SPI.begin(18, 19, 23, 5);

  // Must match your Heltec bridge:
  // frequency 915.0 MHz, BW 125 kHz, SF 9, CR 7, sync word 0x12, power 17 dBm
  int state = radio.begin(915.0, 125.0, 9, 7, 0x12, 17);

  if (state == RADIOLIB_ERR_NONE) {
    radio.setPacketReceivedAction(setFlag);
    radioOk = true;
    radio.startReceive();

    Serial.println("READY");
    Serial.println("# 915MHz BW=125 SF=9 CR=7 sync=0x12 pwr=17dBm");
  } else {
    Serial.print("ERROR|INIT|");
    Serial.println(state);
  }
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();

    if (line.length() > 0 && radioOk) {
      lastTx = line;

      Serial.print("# TX: ");
      Serial.println(line);

      radio.clearPacketReceivedAction();
      int state = radio.transmit(line);

      radio.setPacketReceivedAction(setFlag);
      radio.startReceive();

      if (state == RADIOLIB_ERR_NONE) {
        Serial.println("# TX ok");
      } else {
        Serial.print("TX result: ");
        Serial.println(state);
      }
    }
  }

  if (receivedFlag) {
    receivedFlag = false;

    String msg;
    int state = radio.readData(msg);
    float rssi = radio.getRSSI();
    float snr = radio.getSNR();

    radio.startReceive();

    if (state == RADIOLIB_ERR_NONE) {
      lastRx = msg;

      Serial.println(msg);
      Serial.print("# RX rssi=");
      Serial.print(rssi);
      Serial.print("dBm snr=");
      Serial.print(snr);
      Serial.println("dB");
    } else {
      Serial.print("RX ERR: ");
      Serial.println(state);
    }
  }
}