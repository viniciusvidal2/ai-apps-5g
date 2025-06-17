package com.example.mqttwearable.location

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager as AndroidLocationManager
import android.util.Log
import androidx.core.app.ActivityCompat

class LocationManager(private val context: Context) {
    
    private var androidLocationManager: AndroidLocationManager? = null
    private var currentLocation: Location? = null
    private var locationListener: LocationListener? = null
    
    interface LocationUpdateListener {
        fun onLocationUpdate(latitude: Double, longitude: Double)
        fun onLocationError(error: String)
    }
    
    private var updateListener: LocationUpdateListener? = null
    
    fun setLocationUpdateListener(listener: LocationUpdateListener) {
        this.updateListener = listener
    }
    
    fun startLocationUpdates() {
        if (!hasLocationPermission()) {
            updateListener?.onLocationError("Permissão de localização não concedida")
            return
        }
        
        androidLocationManager = context.getSystemService(Context.LOCATION_SERVICE) as AndroidLocationManager
        
        locationListener = object : LocationListener {
            override fun onLocationChanged(location: Location) {
                currentLocation = location
                updateListener?.onLocationUpdate(location.latitude, location.longitude)
                Log.d("LocationManager", "Localização atualizada: ${location.latitude}, ${location.longitude}")
            }
            
            override fun onProviderEnabled(provider: String) {
                Log.d("LocationManager", "Provedor de localização habilitado: $provider")
            }
            
            override fun onProviderDisabled(provider: String) {
                Log.d("LocationManager", "Provedor de localização desabilitado: $provider")
                updateListener?.onLocationError("Provedor de localização desabilitado: $provider")
            }
        }
        
        try {
            // Tentar GPS primeiro
            if (androidLocationManager?.isProviderEnabled(AndroidLocationManager.GPS_PROVIDER) == true) {
                androidLocationManager?.requestLocationUpdates(
                    AndroidLocationManager.GPS_PROVIDER,
                    10000L, // 10 segundos
                    10f,    // 10 metros
                    locationListener!!
                )
                Log.d("LocationManager", "GPS habilitado")
            }
            
            // Usar Network como backup
            if (androidLocationManager?.isProviderEnabled(AndroidLocationManager.NETWORK_PROVIDER) == true) {
                androidLocationManager?.requestLocationUpdates(
                    AndroidLocationManager.NETWORK_PROVIDER,
                    10000L, // 10 segundos
                    10f,    // 10 metros
                    locationListener!!
                )
                Log.d("LocationManager", "Network Location habilitado")
            }
            
            // Obter última localização conhecida
            getLastKnownLocation()
            
        } catch (e: SecurityException) {
            Log.e("LocationManager", "Erro de permissão de localização", e)
            updateListener?.onLocationError("Erro de permissão: ${e.message}")
        }
    }
    
    fun stopLocationUpdates() {
        locationListener?.let { listener ->
            try {
                androidLocationManager?.removeUpdates(listener)
                Log.d("LocationManager", "Atualizações de localização interrompidas")
            } catch (e: SecurityException) {
                Log.e("LocationManager", "Erro ao parar atualizações de localização", e)
            }
        }
    }
    
    fun getCurrentLocation(): Pair<Double, Double>? {
        return currentLocation?.let { Pair(it.latitude, it.longitude) }
    }
    
    private fun getLastKnownLocation() {
        if (!hasLocationPermission()) return
        
        try {
            val gpsLocation = androidLocationManager?.getLastKnownLocation(AndroidLocationManager.GPS_PROVIDER)
            val networkLocation = androidLocationManager?.getLastKnownLocation(AndroidLocationManager.NETWORK_PROVIDER)
            
            val bestLocation = when {
                gpsLocation != null && networkLocation != null -> {
                    if (gpsLocation.time > networkLocation.time) gpsLocation else networkLocation
                }
                gpsLocation != null -> gpsLocation
                networkLocation != null -> networkLocation
                else -> null
            }
            
            bestLocation?.let { location ->
                currentLocation = location
                updateListener?.onLocationUpdate(location.latitude, location.longitude)
                Log.d("LocationManager", "Última localização conhecida: ${location.latitude}, ${location.longitude}")
            }
        } catch (e: SecurityException) {
            Log.e("LocationManager", "Erro ao obter última localização conhecida", e)
        }
    }
    
    private fun hasLocationPermission(): Boolean {
        return ActivityCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED ||
        ActivityCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_COARSE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
    }
} 