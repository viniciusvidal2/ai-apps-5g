package com.sae5g.mqttwearable.config

/**
 * Configurações específicas para detecção e alerta de queda
 */
object FallenConfig {
    /**
     * Sensibilidade: limiar (m/s²) para considerar que entrou em queda livre.
     * Valores menores tornam mais sensível (detecta mais quedas, porém mais falsos positivos).
     * Recomendações:
     * - 3.0f a 4.5f para dispositivos de pulso
     * - 4.0f (padrão) é um bom equilíbrio
     */
    const val FREE_FALL_THRESHOLD: Float = 4.0f

    /**
     * Sensibilidade: limiar (m/s²) para considerar que houve impacto após a queda.
     * Valores menores tornam mais sensível (pode detectar impactos leves).
     * Recomendações:
     * - 12.0f a 18.0f
     * - 15.0f (padrão) é conservador contra falsos positivos
     */
    const val IMPACT_THRESHOLD: Float = 15.0f

    /**
     * Tempo mínimo (em ms) em queda livre para validar o evento antes do impacto.
     * Valores maiores reduzem falsos positivos (p. ex., gestos rápidos), porém podem perder quedas curtas.
     * Recomendações:
     * - 80ms a 200ms
     * - 100ms (padrão) é adequado para testes de campo
     */
    const val FREE_FALL_DURATION_MS: Long = 100L

    /**
     * Janela de tempo para detecção de padrão de queda
     */
    const val FALL_DETECTION_WINDOW_MS = 3000L  // 3 segundos

    /**
     * Countdown antes de enviar alerta de emergência após queda detectada
     */
    const val FALL_ALERT_COUNTDOWN_SECONDS = 20  // segundos

    /**
     * Intervalo de vibração durante alerta de queda
     */
    const val FALL_ALERT_VIBRATION_INTERVAL_MS = 1000L  // 1 segundo

    /**
     * Duração de cada vibração durante alerta
     */
    const val FALL_ALERT_VIBRATION_DURATION_MS = 500L  // 0.5 segundo
}


