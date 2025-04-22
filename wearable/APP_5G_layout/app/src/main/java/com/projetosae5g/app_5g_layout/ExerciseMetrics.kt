package com.projetosae5g.app_5g_layout

import android.util.Log
import androidx.health.services.client.data.DataPointContainer
import androidx.health.services.client.data.DataType

data class ExerciseMetrics(
    val heartRate: Double? = null,
    val distance: Double? = null,
    val calories: Double? = null,
    val heartRateAverage: Double? = null,
    val caloriesDaily: Double? = null,
    val distanceDaily: Double? = null,
    val declineDist: Double? = null,
    val elevationGain: Double? = null,
    val elevationLoss: Double? = null,
    val flatGroundDist: Double? = null,
    val floors: Double? = null,           // Andares
    val floorsDaily: Double? = null,
    val golfShotCount: Double? = null,
    val inclineDist: Double? = null,
    val ritmo: Double? = null,
    val repCount: Double? = null,
    val executingStages: Double? = null,  // ETAPAS EM EXECUÇÃO
    val velocity: Double? = null,
    val stages: Double? = null,           // ETAPAS
    val stepsDaily: Double? = null,
    val stagesPerMinute: Double? = null,  // ETAPAS_PER_MINUTO
    val swimmingLapCount: Double? = null,
    val swimmingStrokes: Double? = null,
    val caloriesTotal: Double? = null,
    val walkingSteps: Double? = null,
    val userActivityInfo: String? = null,
    val userActivityState: String? = null,
    val vo2Max: Double? = null,
    val elevationAbsolute: Double? = null,
    // Para permissões ou variáveis não numéricas, usamos Boolean ou String
    val activityRecognition: Boolean? = null,
    val bodySensors: Boolean? = null,
    val bodySensorsBackground: Boolean? = null,
    val local: String? = null,
    val accessFineLocation: Boolean? = null
) {
    fun update(latestMetrics: DataPointContainer): ExerciseMetrics {
        // Extração dos dados conhecidos – os demais permanecem inalterados
        val heartRateData = latestMetrics.getData(DataType.HEART_RATE_BPM)
        val newHeartRate = heartRateData.lastOrNull()?.value ?: heartRate
        Log.d("ExerciseMetrics", "heartRateData: $heartRateData, newHeartRate: $newHeartRate")

        val distanceData = latestMetrics.getData(DataType.DISTANCE_TOTAL)
        val newDistance = distanceData?.total ?: distance
        Log.d("ExerciseMetrics", "distanceData: $distanceData, newDistance: $newDistance")

        val caloriesData = latestMetrics.getData(DataType.CALORIES_TOTAL)
        val newCalories = caloriesData?.total ?: calories
        Log.d("ExerciseMetrics", "caloriesData: $caloriesData, newCalories: $newCalories")

        val heartRateStatsData = latestMetrics.getData(DataType.HEART_RATE_BPM_STATS)
        val newHeartRateAverage = heartRateStatsData?.average ?: heartRateAverage
        Log.d("ExerciseMetrics", "heartRateStatsData: $heartRateStatsData, newHeartRateAverage: $newHeartRateAverage")

        return copy(
            heartRate = newHeartRate,
            distance = newDistance,
            calories = newCalories,
            heartRateAverage = newHeartRateAverage
            // Os demais campos permanecem inalterados
        )
    }
}
