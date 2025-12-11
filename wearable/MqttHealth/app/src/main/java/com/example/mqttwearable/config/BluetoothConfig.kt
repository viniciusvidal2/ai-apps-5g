package com.sae5g.mqttwearable.config

/**
 * Configurações para alerta de Bluetooth ligado em horário comercial.
 */
object BluetoothConfig {
    /**
     * Intervalo entre verificações do estado do Bluetooth (ms).
     * Recomendado: 600000L (10 minutos) para evitar consumo excessivo.
     */
    //const val CHECK_INTERVAL_MS: Long = 600000L
    const val CHECK_INTERVAL_MS: Long = 20000L

    /**
     * Intervalo mínimo entre atualizações de GPS, alinhado ao CHECK_INTERVAL_MS.
     */
    const val GPS_UPDATE_INTERVAL_MS: Long = CHECK_INTERVAL_MS

    /**
     * Duração da vibração (ms) quando o Bluetooth estiver ligado
     * dentro da janela ativa. Recomendado: 10000L (10s).
     */
    const val VIBRATION_DURATION_MS: Long = 10000L

    /**
     * Limites geográficos (caixa) onde o alerta deve ser emitido.
     * Coordenadas aproximam um quadrado de teste.
     */
    // JF - Iago (coords anteriores)
    const val ALERT_LATITUDE_MIN = -21.775658435620908
    const val ALERT_LATITUDE_MAX = -21.773863394159424
    const val ALERT_LONGITUDE_MIN = -43.381987607933404
    const val ALERT_LONGITUDE_MAX = -43.380252410127234

    // Novos limites (caixa de Porto Velho, RO)
    /**
    const val ALERT_LATITUDE_MIN = -8.81410166425833
    const val ALERT_LATITUDE_MAX = -8.787001612291837
    const val ALERT_LONGITUDE_MIN = -63.96096884444608
    const val ALERT_LONGITUDE_MAX = -63.937837475111564
    */

    /**
     * Título e texto da notificação de alerta de Bluetooth.
     */
    const val NOTIFICATION_TITLE: String = "Bluetooth Ligado"
    const val NOTIFICATION_TEXT: String = "Bluetooth Ligado, favor desligar"

    /**
     * Verifica se a posição atual está dentro da área configurada.
     */
    fun isWithinAlertArea(latitude: Double?, longitude: Double?): Boolean {
        if (latitude == null || longitude == null) return false

        val insideLatitude = latitude in ALERT_LATITUDE_MIN..ALERT_LATITUDE_MAX
        val insideLongitude = longitude in ALERT_LONGITUDE_MIN..ALERT_LONGITUDE_MAX

        return insideLatitude && insideLongitude
    }
}


