package com.projetosae5g.app_5g_layout

import android.content.Context
import android.util.Log
import com.google.android.gms.common.ConnectionResult
import com.google.android.gms.common.GoogleApiAvailability
import com.google.android.gms.fitness.FitnessLocal
import com.google.android.gms.fitness.data.LocalDataPoint
import com.google.android.gms.fitness.data.LocalDataType
import com.google.android.gms.fitness.request.LocalDataReadRequest
import java.time.LocalDateTime
import java.time.ZoneId
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

class StepCounterService(private val context: Context) {
    private val TAG = "StepCounterService"
    private val localRecordingClient by lazy { FitnessLocal.getLocalRecordingClient(context) }
    
    // Constante para versão mínima do Google Play Services
    private val LOCAL_RECORDING_CLIENT_MIN_VERSION_CODE = 212000000 // Valor aproximado, ajuste se necessário
    
    /**
     * Verifica se o Google Play Services está disponível na versão mínima necessária
     */
    fun isGooglePlayServicesAvailable(): Boolean {
        val hasMinPlayServices = GoogleApiAvailability.getInstance().isGooglePlayServicesAvailable(
            context, 
            LOCAL_RECORDING_CLIENT_MIN_VERSION_CODE
        )
        return hasMinPlayServices == ConnectionResult.SUCCESS
    }
    
    /**
     * Inicia a subscrição para contagem de passos
     */
    suspend fun subscribeToStepCount(): Boolean = withContext(Dispatchers.IO) {
        try {
            // Verifica disponibilidade do Google Play Services
            if (!isGooglePlayServicesAvailable()) {
                Log.w(TAG, "Google Play Services não está disponível na versão mínima necessária")
                return@withContext false
            }
            
            // Subscreve para contagem de passos
            localRecordingClient.subscribe(LocalDataType.TYPE_STEP_COUNT_DELTA)
                .addOnSuccessListener {
                    Log.i(TAG, "Subscrição para contagem de passos realizada com sucesso!")
                }
                .addOnFailureListener { e ->
                    Log.w(TAG, "Problema ao subscrever para contagem de passos", e)
                }
                .await()
            
            return@withContext true
        } catch (e: Exception) {
            Log.e(TAG, "Erro ao subscrever para contagem de passos", e)
            return@withContext false
        }
    }
    
    /**
     * Lê os dados de contagem de passos
     */
    suspend fun readStepCountData(): Int = withContext(Dispatchers.IO) {
        try {
            val endTime = LocalDateTime.now().atZone(ZoneId.systemDefault())
            val startTime = endTime.minusDays(1)
            
            val readRequest = LocalDataReadRequest.Builder()
                .aggregate(LocalDataType.TYPE_STEP_COUNT_DELTA)
                .bucketByTime(1, TimeUnit.DAYS)
                .setTimeRange(startTime.toEpochSecond(), endTime.toEpochSecond(), TimeUnit.SECONDS)
                .build()
                
            var totalSteps = 0
            
            localRecordingClient.readData(readRequest)
                .addOnSuccessListener { response ->
                    for (bucket in response.buckets) {
                        for (dataSet in bucket.dataSets) {
                            Log.i(TAG, "Dados retornados para o tipo: ${dataSet.dataType.name}")
                            for (dp in dataSet.dataPoints) {
                                for (field in dp.dataType.fields) {
                                    val value = dp.getValue(field)
                                    Log.i(TAG, "Campo: ${field.name}, Valor: $value")
                                    // Converter o valor para Int, independentemente do tipo
                                    try {
                                        val intValue = value.toString().toIntOrNull() ?: 0
                                        totalSteps += intValue
                                    } catch (e: Exception) {
                                        Log.e(TAG, "Erro ao converter valor para Int", e)
                                    }
                                }
                            }
                        }
                    }
                    Log.i(TAG, "Total de passos: $totalSteps")
                }
                .addOnFailureListener { e ->
                    Log.e(TAG, "Erro ao ler dados de passos", e)
                }
                .await()
                
            return@withContext totalSteps
        } catch (e: Exception) {
            Log.e(TAG, "Erro ao ler dados de contagem de passos", e)
            return@withContext 0
        }
    }
    
    /**
     * Cancela a subscrição para contagem de passos
     */
    suspend fun unsubscribeFromStepCount(): Boolean = withContext(Dispatchers.IO) {
        try {
            localRecordingClient.unsubscribe(LocalDataType.TYPE_STEP_COUNT_DELTA)
                .addOnSuccessListener {
                    Log.i(TAG, "Cancelamento de subscrição realizado com sucesso!")
                }
                .addOnFailureListener { e ->
                    Log.w(TAG, "Problema ao cancelar subscrição", e)
                }
                .await()
                
            return@withContext true
        } catch (e: Exception) {
            Log.e(TAG, "Erro ao cancelar subscrição para contagem de passos", e)
            return@withContext false
        }
    }
    
    /**
     * Extensão para adicionar suporte a await() para Tasks
     */
    private suspend fun <T> com.google.android.gms.tasks.Task<T>.await(): T {
        return suspendCancellableCoroutine { cont ->
            addOnCompleteListener {
                if (it.isSuccessful) {
                    cont.resume(it.result)
                } else {
                    cont.resumeWithException(it.exception ?: Exception("Tarefa falhou"))
                }
            }
        }
    }
} 