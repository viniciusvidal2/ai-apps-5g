package com.projetosae5g.app_5g_layout

import android.util.Log
import androidx.health.services.client.data.DataPointContainer
import androidx.health.services.client.data.DataType

data class ExerciseMetrics(
    val heartRate: Double? = null,
    val batteryLevel: Int? = null,
    val latitude: Double? = null,
    val longitude: Double? = null
) {
    fun update(data: DataPointContainer): ExerciseMetrics {
        // Processa apenas os dados de batimentos cardíacos
        val points = data.getData(DataType.HEART_RATE_BPM)
        return if (points.isNotEmpty()) {
            copy(heartRate = points[0].value)
        } else {
            this
        }
    }
    
    // Método para atualizar as coordenadas GPS
    fun updateLocation(lat: Double?, lon: Double?): ExerciseMetrics {
        return copy(latitude = lat, longitude = lon)
    }
}
