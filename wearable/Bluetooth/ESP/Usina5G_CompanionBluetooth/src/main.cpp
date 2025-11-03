#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

BLECharacteristic *pCharacteristic;
bool deviceConnected = false;

class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
      deviceConnected = true;
      Serial.println("Conectado!");
    };
    void onDisconnect(BLEServer* pServer) {
      deviceConnected = false;
      Serial.println("Desconectado!");
      delay(500);
      BLEDevice::startAdvertising();
      Serial.println("Aguardando conexao...");
    }
};

class MyCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) {
      std::string value = pCharacteristic->getValue();
      if (value.length() > 0) {
        Serial.print("Recebido: ");
        Serial.println(value.c_str());
      }
    }
};

void setup() {
  Serial.begin(115200);
  Serial.println("\nIniciando BLE...");

  BLEDevice::init("ESP32_Usina5G");
  BLEServer *pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  BLEService *pService = pServer->createService(BLEUUID((uint16_t)0x181A));
  
  pCharacteristic = pService->createCharacteristic(
    BLEUUID((uint16_t)0x2A58),
    BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE
  );
  
  pCharacteristic->setCallbacks(new MyCallbacks());
  pCharacteristic->addDescriptor(new BLE2902());
  
  pService->start();

  BLEAdvertising *pAdvertising = pServer->getAdvertising();
  pAdvertising->start();

  Serial.println("BLE ATIVO!");
  Serial.println("Nome: ESP32_Usina5G");
  Serial.println("Aguardando conexao...");
}

void loop() {
  delay(1000);
}