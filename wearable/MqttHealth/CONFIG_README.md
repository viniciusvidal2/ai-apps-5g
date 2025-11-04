# Configurações de Tempo do Aplicativo MqttHealth

## 📁 Localização
Todas as constantes de tempo estão centralizadas em:
```
app/src/main/java/com/example/mqttwearable/config/AppConfig.kt
```

## ⏱️ Configurações Disponíveis

### 1. MQTT / Dados de Saúde
- **`HEALTH_DATA_SEND_INTERVAL_MS`** = `600000L` (10 minutos)
  - Intervalo de envio de dados de saúde via MQTT
  - Valores sugeridos: 60000L (1 min), 300000L (5 min), 600000L (10 min)

- **`HEALTH_DATA_COUNTDOWN_MS`** = `594000L` (9 min 54s)
  - Tempo do contador visual na MainActivity
  - Deve ser = `HEALTH_DATA_SEND_INTERVAL_MS - UI_SENDING_FEEDBACK_DELAY_MS`

- **`UI_SENDING_FEEDBACK_DELAY_MS`** = `6000L` (6 segundos)
  - Tempo que mostra "Enviando..." na UI antes de reiniciar o contador

- **`TIMER_SYNC_DELAY_MS`** = `3000L` (3 segundos)
  - Delay inicial antes de começar o timer (sincronização)

### 2. SpO2 (Saturação de Oxigênio)
- **`SPO2_MEASUREMENT_DURATION_MS`** = `35000L` (35 segundos)
  - Duração de cada medição de SpO2

- **`SPO2_MEASUREMENT_INTERVAL_MS`** = `3600000L` (1 hora)
  - Intervalo entre medições automáticas de SpO2

- **`SPO2_DATA_VALIDITY_MS`** = `1800000L` (30 minutos)
  - Tempo de validade dos dados de SpO2 armazenados

### 3. Detecção de Queda
- **`FALL_DETECTION_WINDOW_MS`** = `3000L` (3 segundos)
  - Janela de tempo para detecção de padrão de queda

- **`FALL_ALERT_COUNTDOWN_SECONDS`** = `10` (10 segundos)
  - Countdown antes de enviar alerta de emergência após queda detectada

- **`FALL_ALERT_VIBRATION_INTERVAL_MS`** = `1000L` (1 segundo)
  - Intervalo entre vibrações durante alerta de queda

- **`FALL_ALERT_VIBRATION_DURATION_MS`** = `500L` (0.5 segundo)
  - Duração de cada vibração durante alerta

### 4. GPS / Localização
- **`GPS_UPDATE_INTERVAL_MS`** = `10000L` (10 segundos)
  - Intervalo mínimo entre atualizações de GPS

- **`GPS_MIN_DISTANCE_METERS`** = `10f` (10 metros)
  - Distância mínima para atualização de GPS

### 5. MQTT Conexão
- **`MQTT_CONNECTION_TIMEOUT_SECONDS`** = `10`
  - Timeout para conexão MQTT

- **`MQTT_KEEP_ALIVE_INTERVAL_SECONDS`** = `20`
  - Intervalo de keep-alive MQTT

### 6. Acelerômetro
- **`ACCELEROMETER_PUBLISH_INTERVAL_MS`** = `1000L` (1 segundo)
  - Intervalo de publicação de dados do acelerômetro (quando ativado)
  - **NOTA:** Atualmente desativado no app

## 🛠️ Funções Auxiliares

O `AppConfig` também inclui funções para conversão de tempo:

```kotlin
// Conversões
AppConfig.msToSeconds(ms: Long): Long
AppConfig.secondsToMs(seconds: Long): Long
AppConfig.msToMinutes(ms: Long): Long
AppConfig.minutesToMs(minutes: Long): Long

// Formatação
AppConfig.formatMsToTime(ms: Long): String  // Retorna "MM:SS"
```

## 📝 Como Usar

### Importar no arquivo Kotlin:
```kotlin
import com.sae5g.mqttwearable.config.AppConfig
```

### Usar as constantes:
```kotlin
// Exemplo 1: Definir intervalo de envio
val sendInterval = AppConfig.HEALTH_DATA_SEND_INTERVAL_MS

// Exemplo 2: Usar countdown de queda
alertCountdown = AppConfig.FALL_ALERT_COUNTDOWN_SECONDS

// Exemplo 3: Configurar GPS
locationManager.requestLocationUpdates(
    GPS_PROVIDER,
    AppConfig.GPS_UPDATE_INTERVAL_MS,
    AppConfig.GPS_MIN_DISTANCE_METERS,
    locationListener
)

// Exemplo 4: Formatar tempo
val tempoFormatado = AppConfig.formatMsToTime(600000L)  // "10:00"
```

## ✅ Arquivos Atualizados

Os seguintes arquivos já foram atualizados para usar `AppConfig`:

1. ✅ `health/HealthPublisher.kt`
2. ✅ `health/HealthForegroundService.kt`
3. ✅ `presentation/MainActivity.kt`
4. ✅ `presentation/AccelerometerActivity.kt`
5. ✅ `presentation/EmergencyAlertActivity.kt`
6. ✅ `presentation/SpO2Activity.kt`
7. ✅ `data/SpO2DataManager.kt`
8. ✅ `sensors/FallDetector.kt`
9. ✅ `location/LocationManager.kt`

## 🎯 Benefícios da Centralização

1. **Manutenção Fácil**: Altere o tempo em um único lugar
2. **Consistência**: Todos os componentes usam os mesmos valores
3. **Documentação**: Todas as configurações estão documentadas
4. **Flexibilidade**: Fácil de ajustar para diferentes necessidades
5. **Sem Hardcoding**: Valores não estão espalhados pelo código

## 🔄 Para Alterar Intervalos

**Exemplo: Mudar envio de dados para 5 minutos**

1. Abra `AppConfig.kt`
2. Altere:
```kotlin
const val HEALTH_DATA_SEND_INTERVAL_MS = 300000L  // 5 minutos
const val HEALTH_DATA_COUNTDOWN_MS = 294000L      // 4 min 54s
```
3. Recompile o app
4. Pronto! Todos os componentes usarão o novo intervalo

---

**Data de Criação**: Novembro 2025  
**Versão**: 1.0

