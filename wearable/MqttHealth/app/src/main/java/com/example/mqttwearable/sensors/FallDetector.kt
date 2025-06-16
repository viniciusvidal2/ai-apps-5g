package com.example.mqttwearable.sensors

import kotlin.math.sqrt

class FallDetector {
    
    // Constantes para detecção de queda
    private val FREE_FALL_THRESHOLD = 4.0f  // m/s² - valor menos restritivo
    private val IMPACT_THRESHOLD = 15.0f    // m/s² - valor menos restritivo
    private val FREE_FALL_DURATION_MS = 100L // duração menor para testes
    private val DETECTION_WINDOW_MS = 3000L  // janela maior para testes
    

    
    // Estado da detecção
    private var isInFreeFall = false
    private var freeFallStartTime = 0L
    private var freeFallDuration = 0L
    private var hasImpactOccurred = false
    private var detectionStartTime = 0L
    
    // Buffer para suavizar leituras
    private val accelerationBuffer = mutableListOf<Float>()
    private val BUFFER_SIZE = 5
    
    interface FallDetectionListener {
        fun onFallDetected()
        fun onStateChanged(state: String, magnitude: Float)
    }
    
    private var listener: FallDetectionListener? = null
    
    fun setFallDetectionListener(listener: FallDetectionListener) {
        this.listener = listener
    }
    

    
    fun processSensorData(x: Float, y: Float, z: Float): Boolean {
        val magnitude = calculateMagnitude(x, y, z)
        val smoothedMagnitude = addToBufferAndSmooth(magnitude)
        
        val currentTime = System.currentTimeMillis()
        
        // Notificar estado atual
        listener?.onStateChanged(getDetectionState(), smoothedMagnitude)
        
        // Detectar início de queda livre
        if (!isInFreeFall && smoothedMagnitude < FREE_FALL_THRESHOLD) {
            isInFreeFall = true
            freeFallStartTime = currentTime
            detectionStartTime = currentTime
            hasImpactOccurred = false
        }
        
        // Verificar duração da queda livre
        if (isInFreeFall) {
            freeFallDuration = currentTime - freeFallStartTime
            
            // Se saiu da queda livre antes do tempo mínimo, reset
            if (smoothedMagnitude >= FREE_FALL_THRESHOLD && freeFallDuration < FREE_FALL_DURATION_MS) {
                resetDetection()
                return false
            }
        }
        
        // Detectar impacto após queda livre válida
        if (isInFreeFall && 
            freeFallDuration >= FREE_FALL_DURATION_MS && 
            smoothedMagnitude > IMPACT_THRESHOLD) {
            
            hasImpactOccurred = true
            isInFreeFall = false
        }
        
        // Verificar se temos uma queda completa válida
        if (hasImpactOccurred && 
            (currentTime - detectionStartTime) <= DETECTION_WINDOW_MS) {
            
            // Queda detectada!
            resetDetection()
            listener?.onFallDetected()
            return true
        }
        
        // Timeout da janela de detecção
        if (currentTime - detectionStartTime > DETECTION_WINDOW_MS) {
            resetDetection()
        }
        
        return false
    }
    

    
    private fun calculateMagnitude(x: Float, y: Float, z: Float): Float {
        return sqrt(x * x + y * y + z * z)
    }
    
    private fun addToBufferAndSmooth(magnitude: Float): Float {
        accelerationBuffer.add(magnitude)
        if (accelerationBuffer.size > BUFFER_SIZE) {
            accelerationBuffer.removeAt(0)
        }
        return accelerationBuffer.average().toFloat()
    }
    
    private fun resetDetection() {
        isInFreeFall = false
        freeFallStartTime = 0L
        freeFallDuration = 0L
        hasImpactOccurred = false
        detectionStartTime = 0L
    }
    
    // Métodos para debug/monitoramento
    fun getDetectionState(): String {
        return when {
            isInFreeFall -> "Queda Livre (${freeFallDuration}ms)"
            hasImpactOccurred -> "Impacto Detectado"
            else -> "Monitorando"
        }
    }
    
    fun isCurrentlyDetecting(): Boolean {
        return isInFreeFall || hasImpactOccurred
    }
    
    fun getDebugInfo(): String {
        return """
            Thresholds: Queda=${FREE_FALL_THRESHOLD} | Impacto=${IMPACT_THRESHOLD}
            Estado: ${getDetectionState()}
            Tempo queda livre: ${freeFallDuration}ms
        """.trimIndent()
    }
} 