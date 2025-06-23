package com.projetosae5g.app_5g_layout.worker

import android.content.Context
import android.util.Log
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.projetosae5g.app_5g_layout.MainApplication
import com.projetosae5g.app_5g_layout.StepCounterService
import com.projetosae5g.app_5g_layout.data.Repository

private const val TAG = "StepCounterWorker"

class StepCounterWorker(
    appContext: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(appContext, workerParams) {

    override suspend fun doWork(): Result {
        Log.d(TAG, "Iniciando worker...")

        val mainApplication = applicationContext as MainApplication
        val repository = mainApplication.repository
        val stepCounter = mainApplication.stepCounterService

        val stepsSinceLastReboot = stepCounter.readStepCountData()
        if (stepsSinceLastReboot == 0) return Result.success()

        Log.d(TAG, "Passos recebidos do sensor: $stepsSinceLastReboot")
        repository.storeSteps(stepsSinceLastReboot.toLong())

        Log.d(TAG, "Finalizando worker...")
        return Result.success()
    }
} 