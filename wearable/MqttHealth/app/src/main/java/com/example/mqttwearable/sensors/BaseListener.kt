package com.example.mqttwearable.sensors

import android.os.Handler
import android.util.Log
import com.samsung.android.service.health.tracking.HealthTracker

open class BaseListener {
    
    private val appTag = "BaseListener"
    
    private var handler: Handler? = null
    private var healthTracker: HealthTracker? = null
    private var isHandlerRunning = false
    
    private var trackerEventListener: HealthTracker.TrackerEventListener? = null
    
    fun setHealthTracker(tracker: HealthTracker) {
        healthTracker = tracker
    }
    
    fun setHandler(handler: Handler) {
        this.handler = handler
    }
    
    fun setHandlerRunning(handlerRunning: Boolean) {
        isHandlerRunning = handlerRunning
    }
    
    fun setTrackerEventListener(tracker: HealthTracker.TrackerEventListener) {
        trackerEventListener = tracker
    }
    
    fun startTracker() {
        Log.i(appTag, "startTracker called ")
        healthTracker?.let { tracker ->
            Log.d(appTag, "healthTracker: $tracker")
            trackerEventListener?.let { listener ->
                Log.d(appTag, "trackerEventListener: $listener")
                if (!isHandlerRunning) {
                    handler?.post {
                        tracker.setEventListener(listener)
                        setHandlerRunning(true)
                    }
                }
            }
        }
    }
    
    fun stopTracker() {
        Log.i(appTag, "stopTracker called ")
        healthTracker?.let { tracker ->
            Log.d(appTag, "healthTracker: $tracker")
            trackerEventListener?.let { listener ->
                Log.d(appTag, "trackerEventListener: $listener")
                if (isHandlerRunning) {
                    tracker.unsetEventListener()
                    setHandlerRunning(false)
                    handler?.removeCallbacksAndMessages(null)
                }
            }
        }
    }
} 