package com.example.mqttwearable.data

import android.content.Context
import android.provider.Settings
import android.util.Log

object DeviceIdManager {
    
    private var androidId: String? = null
    
    fun initializeDeviceId(context: Context) {
        if (androidId == null) {
            androidId = Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
            Log.d("DeviceIdManager", "Android ID inicializado: $androidId")
        }
    }
    
    fun getDeviceId(): String {
        return androidId ?: "unknown_device"
    }
    
    fun isInitialized(): Boolean {
        return androidId != null
    }
} 