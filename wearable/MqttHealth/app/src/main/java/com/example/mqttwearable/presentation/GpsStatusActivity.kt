package com.sae5g.mqttwearable.presentation

import android.os.Bundle
import android.widget.TextView
import androidx.activity.ComponentActivity
import com.sae5g.mqttwearable.R
import com.sae5g.mqttwearable.config.BluetoothConfig
import com.sae5g.mqttwearable.location.LocationManager

class GpsStatusActivity : ComponentActivity() {

    private lateinit var locationManager: LocationManager
    private var txtLatitude: TextView? = null
    private var txtLongitude: TextView? = null
    private var txtStatus: TextView? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_gps_status)

        txtLatitude = findViewById(R.id.txtLatitude)
        txtLongitude = findViewById(R.id.txtLongitude)
        txtStatus = findViewById(R.id.txtWorkStatus)

        locationManager = LocationManager(applicationContext)
        locationManager.setLocationUpdateListener(object : LocationManager.LocationUpdateListener {
            override fun onLocationUpdate(latitude: Double, longitude: Double) {
                updateLocation(latitude, longitude)
            }

            override fun onLocationError(error: String) {
                txtStatus?.text = "Erro de localização: $error"
            }
        })

        locationManager.startLocationUpdates()
    }

    private fun updateLocation(latitude: Double, longitude: Double) {
        txtLatitude?.text = String.format("%.6f", latitude)
        txtLongitude?.text = String.format("%.6f", longitude)

        val working = BluetoothConfig.isWithinAlertArea(latitude, longitude)
        txtStatus?.text = if (working) "No trabalho" else "Fora do trabalho"
    }

    override fun onDestroy() {
        super.onDestroy()
        locationManager.stopLocationUpdates()
    }
}

