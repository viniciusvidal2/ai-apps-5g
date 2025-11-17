package com.sae5g.mqttwearable.config

/**
 * Configurações centralizadas da aplicação
 * Todas as constantes de tempo e intervalos do app estão aqui
 */
object AppConfig {
    
    // ========== MQTT / HEALTH DATA ==========
    
    /**
     * Intervalo de envio de dados de saúde via MQTT
     * Valores sugeridos:
     * - 60000L = 1 minuto
     * - 300000L = 5 minutos
     * - 600000L = 10 minutos (PADRÃO)
     */
    const val HEALTH_DATA_SEND_INTERVAL_MS = 1*600000L  // 10 minutos

    /**
     * Tempo que mostra "Enviando..." na UI antes de reiniciar o contador
     */
    const val UI_SENDING_FEEDBACK_DELAY_MS = 6000L  // 6 segundos
    
    /**
     * Tempo do countdown visual na MainActivity
     * Deve ser = HEALTH_DATA_SEND_INTERVAL_MS - UI_SENDING_FEEDBACK_DELAY_MS
     */
    const val HEALTH_DATA_COUNTDOWN_MS = HEALTH_DATA_SEND_INTERVAL_MS - UI_SENDING_FEEDBACK_DELAY_MS  // 9 min 54s
    

    
    /**
     * Delay inicial antes de começar o timer (sincronização com HealthPublisher)
     */
    const val TIMER_SYNC_DELAY_MS = 3000L  // 3 segundos
    
    
    // ========== SPO2 (SATURAÇÃO DE OXIGÊNIO) ==========
    
    /**
     * Duração de cada medição de SpO2
     */
    const val SPO2_MEASUREMENT_DURATION_MS = 35000L  // 35 segundos
    
    /**
     * Intervalo entre medições automáticas de SpO2
     */
    const val SPO2_MEASUREMENT_INTERVAL_MS = 2*3600000L  // 1 hora
    
    /**
     * Tempo de validade dos dados de SpO2 armazenados
     */
    const val SPO2_DATA_VALIDITY_MS = 2*3600000L   // 30 minutos
    
    
    // ========== DETECÇÃO DE QUEDA ==========
    
    /**
     * Janela de tempo para detecção de padrão de queda
     */
    const val FALL_DETECTION_WINDOW_MS = 10*3000L  // 3 segundos
    
    /**
     * Countdown antes de enviar alerta de emergência após queda detectada
     */
    const val FALL_ALERT_COUNTDOWN_SECONDS = 10  // 10 segundos
    
    /**
     * Intervalo de vibração durante alerta de queda
     */
    const val FALL_ALERT_VIBRATION_INTERVAL_MS = 1000L  // 1 segundo
    
    /**
     * Duração de cada vibração durante alerta
     */
    const val FALL_ALERT_VIBRATION_DURATION_MS = 500L  // 0.5 segundo
    
    
    // ========== GPS / LOCALIZAÇÃO ==========
    
    /**
     * Intervalo mínimo entre atualizações de GPS
     */
    const val GPS_UPDATE_INTERVAL_MS = 2*600000L  // 10 segundos
    
    /**
     * Distância mínima para atualização de GPS (em metros)
     */
    const val GPS_MIN_DISTANCE_METERS = 10f  // 10 metros
    
    
    // ========== MQTT CONEXÃO ==========
    
    /**
     * Timeout para conexão MQTT
     */
    const val MQTT_CONNECTION_TIMEOUT_SECONDS = 10
    
    /**
     * Intervalo de keep-alive MQTT
     */
    const val MQTT_KEEP_ALIVE_INTERVAL_SECONDS = 20
    
    
    // ========== ACELERÔMETRO ==========
    
    /**
     * Intervalo de publicação de dados do acelerômetro (quando ativado)
     * NOTA: Atualmente desativado no app
     */
    const val ACCELEROMETER_PUBLISH_INTERVAL_MS = 100000L  // 1 segundo
    
    
    // ========== HELPERS ==========
    
    /**
     * Converte milissegundos para segundos
     */
    fun msToSeconds(ms: Long): Long = ms / 1000
    
    /**
     * Converte segundos para milissegundos
     */
    fun secondsToMs(seconds: Long): Long = seconds * 1000
    
    /**
     * Converte milissegundos para minutos
     */
    fun msToMinutes(ms: Long): Long = ms / 60000
    
    /**
     * Converte minutos para milissegundos
     */
    fun minutesToMs(minutes: Long): Long = minutes * 60000
    
    /**
     * Formata milissegundos em string legível (MM:SS)
     */
    fun formatMsToTime(ms: Long): String {
        val totalSeconds = ms / 1000
        val minutes = totalSeconds / 60
        val seconds = totalSeconds % 60
        return String.format("%02d:%02d", minutes, seconds)
    }
}

