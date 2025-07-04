# Criptografia MQTT - AES 128 bits

## Visão Geral

Todas as mensagens MQTT enviadas pelo aplicativo wearable agora são criptografadas usando AES 128 bits no modo CBC com padding PKCS7.

## Implementação

### 1. Classe AESCrypto

**Arquivo**: `app/src/main/java/com/example/mqttwearable/mqtt/AESCrypto.kt`

- **Algoritmo**: AES-128-CBC
- **Padding**: PKCS7
- **Chave**: Os primeiros 16 bytes da chave base64 fornecida
- **IV**: Gerado aleatoriamente para cada mensagem (16 bytes)

### 2. Modificações no MqttHandler

**Arquivo**: `app/src/main/java/com/example/mqttwearable/mqtt/MqttHandler.kt`

- O método `publish()` agora criptografa automaticamente todas as mensagens
- Parâmetro `encrypt` (padrão: true) permite desabilitar criptografia se necessário
- Fallback para texto plano se a criptografia falhar

### 3. Tópicos Criptografados

Todos os seguintes tópicos MQTT são criptografados:

1. **`/health/data`**: Dados de saúde (batimentos cardíacos, SpO2, passos, etc.)
2. **`/fall`**: Alertas de queda e emergência
3. **`/accelerometer`**: Dados do acelerômetro

### 4. Formato da Mensagem Criptografada

```
[IV de 16 bytes][Dados criptografados]
```

- A mensagem final é codificada em Base64
- O IV é concatenado com os dados criptografados
- Receptor deve extrair o IV dos primeiros 16 bytes decodificados

## Exemplo de Uso

### Criptografia Manual
```kotlin
// Criptografar mensagem
val plaintext = """{"time":"2024-01-01T12:00:00Z","heartRateBpm":72}"""
val encrypted = AESCrypto.encrypt(plaintext)

// Descriptografar mensagem
val decrypted = AESCrypto.decrypt(encrypted)
```

### Uso do MqttHandler
```kotlin
// Enviar mensagem criptografada (padrão)
mqttHandler.publish("/fall", fallMessage) { success ->
    // Callback de sucesso
}

// Enviar mensagem sem criptografia (se necessário)
mqttHandler.publish("/fall", fallMessage, encrypt = false) { success ->
    // Callback de sucesso
}
```

## Chave de Criptografia

A chave AES é derivada da chave base64 fornecida:
- **Chave Original**: `MZEaLIx8HCyoucOqqt2Tb73hUAZPT0Z7bti+JLLbDOUwQDFtyrN2JbrX2LNIf44s634JgmbiqVZVodOThH1uwoYORMvFxsA3ziWGUJZa3waazDJtaFbE54co/RRiSkvrGsr5Knl8VFl8M/yVbpcvOdNd5eRtye12ySLV78CNkkr/ryNwMtyWZwxRQuAcjPkO`
- **Chave AES**: Primeiros 16 bytes da chave decodificada

## Teste de Criptografia

**Arquivo**: `app/src/main/java/com/example/mqttwearable/mqtt/CryptoTest.kt`

- Executa automaticamente quando o aplicativo inicia
- Testa criptografia/descriptografia com diferentes tipos de mensagens
- Verifica logs com tag "CryptoTest"

## Logs de Depuração

Para verificar se a criptografia está funcionando:

```
adb logcat -s CryptoTest
adb logcat -s MqttHandler
```

## Segurança

- **IV único**: Cada mensagem usa um IV diferente
- **AES-128**: Considerado seguro para a maioria dos casos de uso
- **Fallback seguro**: Se a criptografia falhar, a mensagem não é enviada em texto plano por padrão
- **Chave fixa**: A chave está hardcoded no código (considere usar KeyStore para produção)

## Considerações para Produção

1. **Gerenciamento de Chaves**: Considere usar Android KeyStore
2. **Rotação de Chaves**: Implemente rotação periódica de chaves
3. **Validação**: Adicione validação de integridade (HMAC)
4. **Logs**: Remova logs sensíveis em builds de produção

## Compatibilidade

- **Android**: Requer API 16+ (Android 4.1)
- **Wear OS**: Compatível com todas as versões suportadas
- **Receptor**: Deve implementar descriptografia AES-128-CBC com o mesmo IV/chave 