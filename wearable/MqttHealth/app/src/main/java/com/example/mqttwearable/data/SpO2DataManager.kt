package com.example.mqttwearable.data

import android.util.Log
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicLong

object SpO2DataManager {
    
    private val currentSpO2Value = AtomicInteger(0)
    private val lastMeasurementTime = AtomicLong(0)
    private const val MEASUREMENT_VALIDITY_MS = 30 * 60 * 1000L // 30 minutos
    
    private val listeners = mutableListOf<SpO2DataListener>()
    
    interface SpO2DataListener {
        fun onSpO2ValueUpdated(spO2Value: Int, timestamp: Long)
    }
    
    fun addListener(listener: SpO2DataListener) {
        synchronized(listeners) {
            listeners.add(listener)
        }
    }
    
    fun removeListener(listener: SpO2DataListener) {
        synchronized(listeners) {
            listeners.remove(listener)
        }
    }
    
    fun updateSpO2Value(spO2Value: Int) {
        if (spO2Value > 0) {
            val timestamp = System.currentTimeMillis()
            currentSpO2Value.set(spO2Value)
            lastMeasurementTime.set(timestamp)
            
            Log.d("SpO2DataManager", "SpO2 atualizado: $spO2Value% em $timestamp")
            
            // Notificar todos os listeners
            synchronized(listeners) {
                listeners.forEach { listener ->
                    try {
                        listener.onSpO2ValueUpdated(spO2Value, timestamp)
                    } catch (e: Exception) {
                        Log.e("SpO2DataManager", "Erro ao notificar listener", e)
                    }
                }
            }
        }
    }
    
    fun getCurrentSpO2(): Int? {
        val currentTime = System.currentTimeMillis()
        val measurementTime = lastMeasurementTime.get()
        
        return if (measurementTime > 0 && (currentTime - measurementTime) <= MEASUREMENT_VALIDITY_MS) {
            val value = currentSpO2Value.get()
            if (value > 0) value else null
        } else {
            null
        }
    }
    
    fun getLastMeasurementTime(): Long {
        return lastMeasurementTime.get()
    }
    
    fun clearData() {
        currentSpO2Value.set(0)
        lastMeasurementTime.set(0)
        Log.d("SpO2DataManager", "Dados de SpO2 limpos")
    }
} 