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
            processHeartRate(data)?.let { updatedMetrics = updatedMetrics.copy(heartRate = it) }
            
            // Processar passos
            processSteps(data)?.let { updatedMetrics = updatedMetrics.copy(steps = it) }
            
            // Processar distância
            processDistance(data)?.let { updatedMetrics = updatedMetrics.copy(distance = it) }
            
            // Processar calorias
            processCalories(data)?.let { updatedMetrics = updatedMetrics.copy(calories = it) }
            
            // Processar velocidade
            processSpeed(data)?.let { updatedMetrics = updatedMetrics.copy(speed = it) }
            
            // Processar elevação
            processElevation(data)?.let { updatedMetrics = updatedMetrics.copy(elevation = it) }
            
            // Processar ritmo
            processPace(data)?.let { updatedMetrics = updatedMetrics.copy(pace = it) }
            
        } catch (e: Exception) {
            Log.e("ExerciseMetrics", "Erro ao processar dados: ${e.message}")
            e.printStackTrace()
        }
        
        return updatedMetrics
    }
    
    private fun processHeartRate(data: DataPointContainer): Double? {
        try {
            val dataPoints = data.getData(DataType.HEART_RATE_BPM)
            if (dataPoints != null && !dataPoints.isEmpty()) {
                val dataPoint = dataPoints.first()
                if (dataPoint is SampleDataPoint<*>) {
                    val value = dataPoint.value as? Double
                    if (value != null) {
                        Log.d("ExerciseMetrics", "Batimentos cardíacos atualizados: $value")
                        return value
                    }
                }
            }
        } catch (e: Exception) {
            Log.e("ExerciseMetrics", "Erro ao processar batimentos cardíacos: ${e.message}")
        }
        return null
    }
    
    private fun processSteps(data: DataPointContainer): Int? {
        try {
            // Tentar STEPS primeiro
            val stepsDataPoints = data.getData(DataType.STEPS)
            if (stepsDataPoints != null && !stepsDataPoints.isEmpty()) {
                val value = stepsDataPoints.first().value as? Long
                if (value != null) {
                    Log.d("ExerciseMetrics", "Passos (STEPS) atualizados: $value")
                    return value.toInt()
                }
            }
            
            // Depois tentar STEPS_DAILY
            val stepsDailyDataPoints = data.getData(DataType.STEPS_DAILY)
            if (stepsDailyDataPoints != null && !stepsDailyDataPoints.isEmpty()) {
                val value = stepsDailyDataPoints.first().value as? Long
                if (value != null) {
                    Log.d("ExerciseMetrics", "Passos (STEPS_DAILY) atualizados: $value")
                    return value.toInt()
                }
            }
        } catch (e: Exception) {
            Log.e("ExerciseMetrics", "Erro ao processar passos: ${e.message}")
        }
        return null
    }
    
    private fun processDistance(data: DataPointContainer): Double? {
        try {
            val dataPoints = data.getData(DataType.DISTANCE)
            if (dataPoints != null && !dataPoints.isEmpty()) {
                val value = dataPoints.first().value as? Double
                if (value != null) {
                    Log.d("ExerciseMetrics", "Distância atualizada: $value")
                    return value
                }
            }
        } catch (e: Exception) {
            Log.e("ExerciseMetrics", "Erro ao processar distância: ${e.message}")
        }
        return null
    }
    
    private fun processCalories(data: DataPointContainer): Double? {
        try {
            val dataPoints = data.getData(DataType.CALORIES)
            if (dataPoints != null && !dataPoints.isEmpty()) {
                val value = dataPoints.first().value as? Double
                if (value != null) {
                    Log.d("ExerciseMetrics", "Calorias atualizadas: $value")
                    return value
                }
            }
        } catch (e: Exception) {
            Log.e("ExerciseMetrics", "Erro ao processar calorias: ${e.message}")
        }
        return null
    }
    
    private fun processSpeed(data: DataPointContainer): Double? {
        try {
            val dataPoints = data.getData(DataType.SPEED)
            if (dataPoints != null && !dataPoints.isEmpty()) {
                val dataPoint = dataPoints.first()
                if (dataPoint is SampleDataPoint<*>) {
                    val value = dataPoint.value as? Double
                    if (value != null) {
                        Log.d("ExerciseMetrics", "Velocidade atualizada: $value")
                        return value
                    }
                }
            }
        } catch (e: Exception) {
            Log.e("ExerciseMetrics", "Erro ao processar velocidade: ${e.message}")
        }
        return null
    }
    
    private fun processElevation(data: DataPointContainer): Double? {
        try {
            val dataPoints = data.getData(DataType.ELEVATION_GAIN)
            if (dataPoints != null && !dataPoints.isEmpty()) {
                val value = dataPoints.first().value as? Double
                if (value != null) {
                    Log.d("ExerciseMetrics", "Elevação atualizada: $value")
                    return value
                }
            }
        } catch (e: Exception) {
            Log.e("ExerciseMetrics", "Erro ao processar elevação: ${e.message}")
        }
        return null
    }
    
    private fun processPace(data: DataPointContainer): Double? {
        try {
            val dataPoints = data.getData(DataType.PACE)
            if (dataPoints != null && !dataPoints.isEmpty()) {
                val dataPoint = dataPoints.first()
                if (dataPoint is SampleDataPoint<*>) {
                    val value = dataPoint.value as? Double
                    if (value != null) {
                        Log.d("ExerciseMetrics", "Ritmo atualizado: $value")
                        return value
                    }
                }
            }
        } catch (e: Exception) {
            Log.e("ExerciseMetrics", "Erro ao processar ritmo: ${e.message}")
        }
        return null
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

