package com.example.mqttwearable.sensors

import android.util.Log
import com.samsung.android.service.health.tracking.HealthTracker
import com.samsung.android.service.health.tracking.data.DataPoint
import com.samsung.android.service.health.tracking.data.ValueKey

class HeartRateListener(private val onHeartRateUpdate: (HeartRateData) -> Unit) : BaseListener() {
    
    private val appTag = "HeartRateListener"
    
    init {
        val trackerEventListener = object : HealthTracker.TrackerEventListener {
            override fun onDataReceived(dataPoints: List<DataPoint>) {
                for (dataPoint in dataPoints) {
                    readValuesFromDataPoint(dataPoint)
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
                        Log.e(appTag, "Erro de permissão")
                    }
                    HealthTracker.TrackerError.SDK_POLICY_ERROR -> {
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
    
    private fun readValuesFromDataPoint(dataPoint: DataPoint) {
        val hrData = HeartRateData()
        val hrIbiList: List<Int>? = dataPoint.getValue(ValueKey.HeartRateSet.IBI_LIST)
        val hrIbiStatus: List<Int>? = dataPoint.getValue(ValueKey.HeartRateSet.IBI_STATUS_LIST)
        
        hrData.status = dataPoint.getValue(ValueKey.HeartRateSet.HEART_RATE_STATUS)
        hrData.hr = dataPoint.getValue(ValueKey.HeartRateSet.HEART_RATE)
        
        if (hrIbiList != null && hrIbiList.isNotEmpty()) {
            hrData.ibi = hrIbiList.last() // Inter-Beat Interval (ms)
        }
        
        if (hrIbiStatus != null && hrIbiStatus.isNotEmpty()) {
            hrData.qIbi = hrIbiStatus.size - 1 // 1: bad, 0: good
        }
        
        onHeartRateUpdate(hrData)
        Log.d(appTag, dataPoint.toString())
    }
} 