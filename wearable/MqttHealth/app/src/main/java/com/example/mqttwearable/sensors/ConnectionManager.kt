package com.example.mqttwearable.sensors

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.util.Log
import com.samsung.android.service.health.tracking.ConnectionListener
import com.samsung.android.service.health.tracking.HealthTracker
import com.samsung.android.service.health.tracking.HealthTrackerException
import com.samsung.android.service.health.tracking.HealthTrackingService
import com.samsung.android.service.health.tracking.data.HealthTrackerType

class ConnectionManager(private val connectionObserver: ConnectionObserver) {
    
    private val appTag = "ConnectionManager"
    private var healthTrackingService: HealthTrackingService? = null
    
    private val connectionListener = object : ConnectionListener {
        override fun onConnectionSuccess() {
            Log.i(appTag, "Connected")
            connectionObserver.onConnectionResult("Conectado ao Samsung Health")
            healthTrackingService?.let { service ->
                if (!isSpO2Available(service)) {
                    Log.i(appTag, "Device does not support SpO2 tracking")
                    connectionObserver.onConnectionResult("SpO2 não suportado neste dispositivo")
                }
                if (!isHeartRateAvailable(service)) {
                    Log.i(appTag, "Device does not support Heart Rate tracking")
                    connectionObserver.onConnectionResult("Heart Rate não suportado neste dispositivo")
                }
            }
        }
        
        override fun onConnectionEnded() {
            Log.i(appTag, "Disconnected")
        }
        
        override fun onConnectionFailed(healthTrackerException: HealthTrackerException) {
            connectionObserver.onError(healthTrackerException)
        }
    }
    
    fun connect(context: Context) {
        healthTrackingService = HealthTrackingService(connectionListener, context)
        healthTrackingService?.connectService()
    }
    
    fun disconnect() {
        healthTrackingService?.disconnectService()
    }
    
    fun initSpO2(spO2Listener: SpO2Listener) {
        try {
            val healthTracker = healthTrackingService?.getHealthTracker(HealthTrackerType.SPO2_ON_DEMAND)
            healthTracker?.let {
                spO2Listener.setHealthTracker(it)
                setHandlerForBaseListener(spO2Listener)
                Log.i(appTag, "SpO2 tracker initialized successfully")
            }
        } catch (e: Exception) {
            Log.e(appTag, "Failed to initialize SpO2 tracker: ${e.message}")
        }
    }
    
    fun initHeartRate(heartRateListener: HeartRateListener) {
        try {
            val healthTracker = healthTrackingService?.getHealthTracker(HealthTrackerType.HEART_RATE_CONTINUOUS)
            healthTracker?.let {
                heartRateListener.setHealthTracker(it)
                setHandlerForBaseListener(heartRateListener)
                Log.i(appTag, "Heart Rate tracker initialized successfully")
            }
        } catch (e: Exception) {
            Log.e(appTag, "Failed to initialize Heart Rate tracker: ${e.message}")
        }
    }
    
    private fun setHandlerForBaseListener(baseListener: BaseListener) {
        baseListener.setHandler(Handler(Looper.getMainLooper()))
    }
    
    private fun isSpO2Available(healthTrackingService: HealthTrackingService): Boolean {
        val availableTrackers = healthTrackingService.trackingCapability?.supportHealthTrackerTypes
        return availableTrackers?.contains(HealthTrackerType.SPO2_ON_DEMAND) == true
    }
    
    private fun isHeartRateAvailable(healthTrackingService: HealthTrackingService): Boolean {
        val availableTrackers = healthTrackingService.trackingCapability?.supportHealthTrackerTypes
        return availableTrackers?.contains(HealthTrackerType.HEART_RATE_CONTINUOUS) == true
    }
}

interface ConnectionObserver {
    fun onConnectionResult(message: String)
    fun onError(exception: HealthTrackerException)
} 