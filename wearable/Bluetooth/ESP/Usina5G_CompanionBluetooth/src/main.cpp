#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// UUIDs para o serviço e característica BLE
#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

// Variáveis globais
BLEServer* pServer = NULL;
BLECharacteristic* pCharacteristic = NULL;
bool deviceConnected = false;
bool oldDeviceConnected = false;

// Callback para eventos de conexão/desconexão
class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
      deviceConnected = true;
      Serial.println("Cliente BLE conectado!");
    };

    void onDisconnect(BLEServer* pServer) {
      deviceConnected = false;
      Serial.println("Cliente BLE desconectado!");
    }
};

// Callback para receber dados via BLE
class MyCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) {
      std::string value = pCharacteristic->getValue();

      if (value.length() > 0) {
        Serial.println("===== Mensagem Recebida via BLE =====");
        Serial.print("Tamanho: ");
        Serial.println(value.length());
        Serial.print("Conteúdo: ");
        for (int i = 0; i < value.length(); i++) {
          Serial.print(value[i]);
        }
        Serial.println();
        Serial.println("=====================================");
      }
    }
};

void setup() {
  // Inicializa comunicação serial
  Serial.begin(115200);
  Serial.println("Iniciando servidor BLE...");

  // Cria o dispositivo BLE
  BLEDevice::init("ESP32_Usina5G");

  // Cria o servidor BLE
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  // Cria o serviço BLE
  BLEService *pService = pServer->createService(SERVICE_UUID);

  // Cria a característica BLE
  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ   |
                      BLECharacteristic::PROPERTY_WRITE  |
                      BLECharacteristic::PROPERTY_NOTIFY |
                      BLECharacteristic::PROPERTY_INDICATE
                    );

  // Adiciona callback para receber dados
  pCharacteristic->setCallbacks(new MyCallbacks());

  // Adiciona descritor para notificações
  pCharacteristic->addDescriptor(new BLE2902());

  // Inicia o serviço
  pService->start();

  // Inicia o anúncio BLE
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(false);
  pAdvertising->setMinPreferred(0x0);  // set value to 0x00 to not advertise this parameter
  BLEDevice::startAdvertising();
  
  Serial.println("Servidor BLE ativo!");
  Serial.println("Aguardando conexão de cliente BLE...");
  Serial.print("Nome do dispositivo: ESP32_Usina5G");
  Serial.println();
}

void loop() {
  // Gerencia reconexão quando cliente desconecta
  if (!deviceConnected && oldDeviceConnected) {
    delay(500); // tempo para stack bluetooth se preparar
    pServer->startAdvertising(); // reinicia anúncio
    Serial.println("Aguardando nova conexão...");
    oldDeviceConnected = deviceConnected;
  }
  
  // Gerencia nova conexão
  if (deviceConnected && !oldDeviceConnected) {
    oldDeviceConnected = deviceConnected;
  }
  
  delay(100);
}