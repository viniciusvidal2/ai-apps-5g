package com.projetosae5g.app_5g_layout.data

import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.time.Instant
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.LocalTime

class Repository(
    private val stepsDao: StepsDao,
) {
    private val TAG = "Repository"

    suspend fun storeSteps(stepsSinceLastReboot: Long) = withContext(Dispatchers.IO) {
        val stepCount = StepCount(
            steps = stepsSinceLastReboot,
            createdAt = Instant.now().toString()
        )
        Log.d(TAG, "Armazenando passos: $stepCount")
        stepsDao.insertAll(stepCount)
    }

    suspend fun loadTodaySteps(): Long = withContext(Dispatchers.IO) {
        val todayAtMidnight = (LocalDateTime.of(LocalDate.now(), LocalTime.MIDNIGHT).toString())
        val todayDataPoints = stepsDao.loadAllStepsFromToday(startDateTime = todayAtMidnight)
        
        when {
            todayDataPoints.isEmpty() -> 0
            else -> {
                val firstDataPointOfTheDay = todayDataPoints.first()
                val latestDataPointSoFar = todayDataPoints.last()

                val todaySteps = latestDataPointSoFar.steps - firstDataPointOfTheDay.steps
                Log.d(TAG, "Passos de hoje: $todaySteps")
                todaySteps
            }
        }
    }
    
    // Método para debug
    private suspend fun printTheWholeStepsTable() = withContext(Dispatchers.IO) {
        val allSteps = stepsDao.getAll()
        Log.d(TAG, "Tabela de passos completa:")
        allSteps.forEach { stepCount ->
            Log.d(TAG, "  ID: ${stepCount.id}, Passos: ${stepCount.steps}, Data: ${stepCount.createdAt}")
        }
    }
} 