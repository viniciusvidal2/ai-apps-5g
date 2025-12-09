package com.sae5g.mqttwearable.config

import java.util.Calendar

/**
 * Configurações para alerta de Bluetooth ligado em horário comercial.
 */
object BluetoothConfig {
    /**
     * Intervalo entre verificações do estado do Bluetooth (ms).
     * Recomendado: 600000L (10 minutos) para evitar consumo excessivo.
     */
    const val CHECK_INTERVAL_MS: Long = 600000L

    /**
     * Duração da vibração (ms) quando o Bluetooth estiver ligado
     * dentro da janela ativa. Recomendado: 10000L (10s).
     */
    const val VIBRATION_DURATION_MS: Long = 10000L

    /**
     * Janela ativa diária (horário local).
     * Início inclusivo (8:00), fim exclusivo (17:00).
     */
    const val ACTIVE_START_HOUR: Int = 8
    const val ACTIVE_END_HOUR: Int = 17

    /**
     * Dias ativos: Segunda a Sexta-feira.
     */
    val ACTIVE_DAYS: Set<Int> = setOf(
        Calendar.MONDAY,
        Calendar.TUESDAY,
        Calendar.WEDNESDAY,
        Calendar.THURSDAY,
        Calendar.FRIDAY
    )

    /**
     * Título e texto da notificação de alerta de Bluetooth.
     */
    const val NOTIFICATION_TITLE: String = "Bluetooth Ligado"
    const val NOTIFICATION_TEXT: String = "Bluetooth Ligado, favor desligar"

    /**
     * Helper para verificar se o momento atual está dentro da janela ativa.
     */
    fun isWithinActiveWindow(now: Calendar = Calendar.getInstance()): Boolean {
        val day = now.get(Calendar.DAY_OF_WEEK)
        if (!ACTIVE_DAYS.contains(day)) return false

        val hour = now.get(Calendar.HOUR_OF_DAY)
        return hour in ACTIVE_START_HOUR until ACTIVE_END_HOUR
    }
}


