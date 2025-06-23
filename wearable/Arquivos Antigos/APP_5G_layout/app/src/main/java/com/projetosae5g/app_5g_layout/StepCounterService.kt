package com.projetosae5g.app_5g_layout

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.util.Log
import kotlinx.coroutines.suspendCancellableCoroutine
import java.time.Instant
import kotlin.coroutines.resume

class StepCounterService(private val context: Context) {
    private val TAG = "StepCounterService"
    private val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val stepSensor = sensorManager.getDefaultSensor(Sensor.TYPE_STEP_COUNTER)
    
    /**
     * Verifica se o sensor de passos está disponível no dispositivo
     */
    fun isStepSensorAvailable(): Boolean {
        return stepSensor != null
    }
    
    /**
     * Compatibilidade com código existente (será removido no futuro)
     */
    fun isGooglePlayServicesAvailable(): Boolean {
        return isStepSensorAvailable()
    }
    
    /**
     * Compatibilidade com código existente (será removido no futuro)
     */
    suspend fun subscribeToStepCount(): Boolean {
        return isStepSensorAvailable()
    }
    
    /**
     * Compatibilidade com código existente (será removido no futuro)
     */
    suspend fun unsubscribeFromStepCount(): Boolean {
        return true
    }
    
    /**
     * Lê os dados de contagem de passos usando o sensor
     */
    suspend fun readStepCountData(): Int {
        if (!isStepSensorAvailable()) {
            Log.w(TAG, "Sensor de passos não disponível neste dispositivo")
            return 0
        }
        
        return suspendCancellableCoroutine { continuation ->
            val listener = object : SensorEventListener {
                var stepsSinceLastReboot = 0
                
                override fun onSensorChanged(event: SensorEvent?) {
                    if (event?.sensor?.type == Sensor.TYPE_STEP_COUNTER) {
                        stepsSinceLastReboot = event.values[0].toInt()
                        Log.d(TAG, "Passos desde a última inicialização: $stepsSinceLastReboot")
                        
                        // Desregistrar o listener após obter o valor
                        sensorManager.unregisterListener(this)
                        
                        // Retornar o valor para o chamador
                        if (continuation.isActive) {
                            continuation.resume(stepsSinceLastReboot)
                        }
                    }
                }
                
                override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {
                    Log.d(TAG, "Precisão alterada para: $accuracy")
                }
            }
            
            val registered = sensorManager.registerListener(
                listener, 
                stepSensor, 
                SensorManager.SENSOR_DELAY_UI
            )
            
            Log.d(TAG, "Sensor de passos registrado: $registered")
            
            // Cancelar se a corrotina for cancelada
            continuation.invokeOnCancellation {
                sensorManager.unregisterListener(listener)
                Log.d(TAG, "Listener de sensor cancelado")
            }
        }
    }
    
    // Futura implementação: Iniciar monitoramento contínuo
    fun startMonitoring(listener: StepCountListener) {
        // Implementação futura
    }
    
    // Futura implementação: Parar monitoramento
    fun stopMonitoring() {
        // Implementação futura
    }
    
    interface StepCountListener {
        fun onStepCountChanged(steps: Int)
    }
} 