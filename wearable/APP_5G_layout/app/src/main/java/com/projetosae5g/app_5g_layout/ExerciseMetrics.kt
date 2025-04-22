package com.projetosae5g.app_5g_layout

import android.util.Log
import androidx.health.services.client.data.DataPointContainer
import androidx.health.services.client.data.DataType

data class ExerciseMetrics(
    val heartRate: Double? = null,
    val batteryLevel: Int? = null
) {
    fun update(latestMetrics: DataPointContainer): ExerciseMetrics {
        // Extrai apenas os dados de batimentos cardíacos
        val heartRateData = latestMetrics.getData(DataType.HEART_RATE_BPM)
        val newHeartRate = heartRateData.lastOrNull()?.value ?: heartRate
        Log.d("ExerciseMetrics", "heartRateData: $heartRateData, newHeartRate: $newHeartRate")

        return copy(
            heartRate = newHeartRate
            // O nível da bateria será atualizado separadamente
        )
    }
}
