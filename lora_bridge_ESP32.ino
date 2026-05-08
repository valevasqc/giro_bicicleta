// lora_bridge_ESP32.ino — Generic ESP32 + SX1276 module serial bridge (no OLED).
//   - PA_BOOST forced via setOutputPower(20, false). Most generic SX1276 modules
//     wire PA_BOOST only.
// Serial protocol identical to the V4 / V2 bridges: READY / ERROR|INIT|<code>
// / raw payload / # comments.

#include <RadioLib.h>
#include <SPI.h>

// SX1276 wiring:
// NSS/CS = 5, DIO0 = 26, RST = 14, DIO1 = 33
#define LORA_SCK   18
#define LORA_MISO  19
#define LORA_MOSI  23
#define LORA_NSS   5
#define LORA_RST   14
#define LORA_DIO0  26
#define LORA_DIO1  33

SX1276 radio = new Module(LORA_NSS, LORA_DIO0, LORA_RST, LORA_DIO1);

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

  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_NSS);

  // 915 MHz / BW125 / SF9 / CR4/7 / sync 0x12 / 17 dBm placeholder / preamble 8 / gain auto
  int state = radio.begin(915.0, 125.0, 9, 7, 0x12, 17, 8, 0);

  if (state == RADIOLIB_ERR_NONE) {
    // Force PA_BOOST output (false = useRfo=false → PA_BOOST).
    radio.setOutputPower(20, false);
    // RX gain stays at AGC default — adapts across distance.
    radio.setPacketReceivedAction(setFlag);
    radioOk = true;
    radio.startReceive();

    Serial.println("READY");
    Serial.println("# 915MHz BW=125 SF=9 CR=7 sync=0x12 pwr=20dBm PA_BOOST");
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
