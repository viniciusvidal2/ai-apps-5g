package com.example.mqttwearable.sensors

import android.util.Log
import com.samsung.android.service.health.tracking.HealthTracker
import com.samsung.android.service.health.tracking.data.DataPoint
import com.samsung.android.service.health.tracking.data.ValueKey
import com.example.mqttwearable.R

class SpO2Listener(private val onSpO2Update: (Int, Int) -> Unit) : BaseListener() {
    
    private val appTag = "SpO2Listener"
    
    init {
        val trackerEventListener = object : HealthTracker.TrackerEventListener {
            override fun onDataReceived(dataPoints: List<DataPoint>) {
                for (data in dataPoints) {
                    updateSpO2(data)
                }
            }
            
            override fun onFlushCompleted() {
                Log.i(appTag, " onFlushCompleted called")
            }
            
            override fun onError(trackerError: HealthTracker.TrackerError) {
                Log.e(appTag, " onError called: $trackerError")
                setHandlerRunning(false)
                when (trackerError) {
                    HealthTracker.TrackerError.PERMISSION_ERROR -> {
                        // Notificar erro de permissão
                        Log.e(appTag, "Erro de permissão")
                    }
                    HealthTracker.TrackerError.SDK_POLICY_ERROR -> {
                        // Notificar erro de política SDK
                        Log.e(appTag, "Erro de política SDK")
                    }
                    else -> {
                        Log.e(appTag, "Erro desconhecido: $trackerError")
                    }
                }
            }
        }
        setTrackerEventListener(trackerEventListener)
    }
    
    private fun updateSpO2(dataPoint: DataPoint) {
        val status = dataPoint.getValue(ValueKey.SpO2Set.STATUS)
        var spO2Value = 0
        if (status == SpO2Status.MEASUREMENT_COMPLETED) {
            spO2Value = dataPoint.getValue(ValueKey.SpO2Set.SPO2)
        }
        onSpO2Update(status, spO2Value)
        Log.d(appTag, dataPoint.toString())
    }
} 