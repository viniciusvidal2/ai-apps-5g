package com.projetosae5g.app_5g_layout

import android.util.Log
import androidx.health.services.client.data.DataPointContainer
import androidx.health.services.client.data.DataType
import androidx.health.services.client.data.SampleDataPoint

data class ExerciseMetrics(
    val heartRate: Double? = null,
    val batteryLevel: Int? = null,
    val latitude: Double? = null,
    val longitude: Double? = null,
    val steps: Int? = null,
    val distance: Double? = null,
    val calories: Double? = null,
    val speed: Double? = null,
    val elevation: Double? = null,
    val pace: Double? = null
) {
    fun update(data: DataPointContainer): ExerciseMetrics {
        var updatedMetrics = this
        
        try {
            // Processar batimentos cardíacos
            data.getData(DataType.HEART_RATE_BPM)?.let { dataPoints ->
                if (dataPoints.isNotEmpty()) {
                    val heartRateValue = (dataPoints[0] as? SampleDataPoint<Double>)?.value
                    heartRateValue?.let {
                        updatedMetrics = updatedMetrics.copy(heartRate = it)
                        Log.d("ExerciseMetrics", "Batimentos cardíacos atualizados: $it")
                    }
                }
            }
            
            // Processar passos
            data.getData(DataType.STEPS)?.let { dataPoints ->
                if (dataPoints.isNotEmpty()) {
                    val stepsValue = dataPoints[0].value as? Long
                    stepsValue?.let {
                        updatedMetrics = updatedMetrics.copy(steps = it.toInt())
                        Log.d("ExerciseMetrics", "Passos atualizados: $it")
                    }
                }
            }
            
            // Processar distância
            data.getData(DataType.DISTANCE)?.let { dataPoints ->
                if (dataPoints.isNotEmpty()) {
                    val distanceValue = dataPoints[0].value as? Double
                    distanceValue?.let {
                        updatedMetrics = updatedMetrics.copy(distance = it)
                        Log.d("ExerciseMetrics", "Distância atualizada: $it")
                    }
                }
            }
            
            // Processar calorias
            data.getData(DataType.CALORIES)?.let { dataPoints ->
                if (dataPoints.isNotEmpty()) {
                    val caloriesValue = dataPoints[0].value as? Double
                    caloriesValue?.let {
                        updatedMetrics = updatedMetrics.copy(calories = it)
                        Log.d("ExerciseMetrics", "Calorias atualizadas: $it")
                    }
                }
            }
            
            // Processar velocidade
            data.getData(DataType.SPEED)?.let { dataPoints ->
                if (dataPoints.isNotEmpty()) {
                    val speedValue = (dataPoints[0] as? SampleDataPoint<Double>)?.value
                    speedValue?.let {
                        updatedMetrics = updatedMetrics.copy(speed = it)
                        Log.d("ExerciseMetrics", "Velocidade atualizada: $it")
                    }
                }
            }
            
            // Processar elevação
            data.getData(DataType.ELEVATION_GAIN)?.let { dataPoints ->
                if (dataPoints.isNotEmpty()) {
                    val elevationValue = dataPoints[0].value as? Double
                    elevationValue?.let {
                        updatedMetrics = updatedMetrics.copy(elevation = it)
                        Log.d("ExerciseMetrics", "Elevação atualizada: $it")
                    }
                }
            }
            
            // Processar ritmo
            data.getData(DataType.PACE)?.let { dataPoints ->
                if (dataPoints.isNotEmpty()) {
                    val paceValue = (dataPoints[0] as? SampleDataPoint<Double>)?.value
                    paceValue?.let {
                        updatedMetrics = updatedMetrics.copy(pace = it)
                        Log.d("ExerciseMetrics", "Ritmo atualizado: $it")
                    }
                }
            }
        } catch (e: Exception) {
            Log.e("ExerciseMetrics", "Erro ao processar dados: ${e.message}")
            e.printStackTrace()
        }
        
        return updatedMetrics
    }
    
    // Método para atualizar as coordenadas GPS
    fun updateLocation(lat: Double?, lon: Double?): ExerciseMetrics {
        return copy(latitude = lat, longitude = lon)
    }
    
    // Método para atualizar contagem de passos da Recording API
    fun updateSteps(steps: Int): ExerciseMetrics {
        if (steps > 0) {
            Log.d("ExerciseMetrics", "Passos atualizados via Recording API: $steps")
            return copy(steps = steps)
        }
        return this
    }
    
    // Método para calcular distância com base na contagem de passos (estimativa)
    fun calculateDistanceFromSteps(): ExerciseMetrics {
        // Média de distância de passo: ~0.762m (considerando 80cm como média)
        val stepLengthMeters = 0.762
        steps?.let { stepCount ->
            val estimatedDistance = stepCount * stepLengthMeters
            return copy(distance = estimatedDistance)
        }
        return this
    }
    
    // Método para calcular calorias com base na contagem de passos (estimativa)
    fun calculateCaloriesFromSteps(): ExerciseMetrics {
        // Média de calorias por passo: ~0.04 calorias por passo
        val caloriesPerStep = 0.04
        steps?.let { stepCount ->
            val estimatedCalories = stepCount * caloriesPerStep
            return copy(calories = estimatedCalories)
        }
        return this
    }
}
