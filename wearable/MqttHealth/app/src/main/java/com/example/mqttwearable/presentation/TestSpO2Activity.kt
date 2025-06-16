package com.example.mqttwearable.presentation

import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.core.app.ActivityCompat
import com.example.mqttwearable.R
import com.samsung.android.service.health.tracking.ConnectionListener
import com.samsung.android.service.health.tracking.HealthTrackingService
import com.samsung.android.service.health.tracking.HealthTrackerException

class TestSpO2Activity : Activity() {

    private val appTag = "TestSpO2Activity"
    private var healthTrackingService: HealthTrackingService? = null
    private var connected = false
    private var permissionGranted = false

    private lateinit var txtStatus: TextView
    private lateinit var butTest: Button
    private lateinit var btnBack: Button

    private val connectionListener = object : ConnectionListener {
        override fun onConnectionSuccess() {
            Log.i(appTag, "Connected to HealthTrackingService")
            connected = true
            runOnUiThread {
                txtStatus.text = "Conectado com sucesso ao Samsung Health!"
                Toast.makeText(applicationContext, "Conexão estabelecida", Toast.LENGTH_LONG).show()
                
                // Listar trackers disponíveis
                healthTrackingService?.let { service ->
                    try {
                        val availableTrackers = service.trackingCapability?.supportHealthTrackerTypes
                        availableTrackers?.forEach { trackerType ->
                            Log.d(appTag, "Tracker disponível: $trackerType")
                        }
                        val trackerList = availableTrackers?.joinToString(", ") { it.toString() }
                        txtStatus.text = "Conectado! Trackers: $trackerList"
                    } catch (e: Exception) {
                        Log.e(appTag, "Erro ao listar trackers: ${e.message}")
                        txtStatus.text = "Conectado, mas erro ao listar trackers: ${e.message}"
                    }
                }
            }
        }

        override fun onConnectionEnded() {
            Log.i(appTag, "Disconnected from HealthTrackingService")
            connected = false
            runOnUiThread {
                txtStatus.text = "Conexão encerrada"
            }
        }

        override fun onConnectionFailed(healthTrackerException: HealthTrackerException) {
            Log.e(appTag, "Connection failed: ${healthTrackerException.message}")
            runOnUiThread {
                txtStatus.text = "Falha na conexão: ${healthTrackerException.message}"
                Toast.makeText(applicationContext, "Erro: ${healthTrackerException.message}", Toast.LENGTH_LONG).show()
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_spo2)

        initializeViews()
        setupClickListeners()

        if (ActivityCompat.checkSelfPermission(applicationContext, Manifest.permission.BODY_SENSORS) == PackageManager.PERMISSION_DENIED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.BODY_SENSORS), 0)
        } else {
            permissionGranted = true
            connectToHealthService()
        }
    }

    private fun initializeViews() {
        txtStatus = findViewById(R.id.txtStatus)
        butTest = findViewById(R.id.butStart)
        btnBack = findViewById(R.id.btnBack)
        
        butTest.text = "Testar Conexão"
        txtStatus.text = "Aguardando teste de conexão..."
    }

    private fun setupClickListeners() {
        butTest.setOnClickListener {
            if (!connected) {
                connectToHealthService()
            } else {
                txtStatus.text = "Já conectado!"
            }
        }

        btnBack.setOnClickListener {
            finish()
        }
    }

    private fun connectToHealthService() {
        if (!permissionGranted) {
            Toast.makeText(this, "Permissão necessária", Toast.LENGTH_SHORT).show()
            return
        }

        try {
            txtStatus.text = "Tentando conectar ao Samsung Health..."
            healthTrackingService = HealthTrackingService(connectionListener, applicationContext)
            healthTrackingService?.connectService()
            Log.i(appTag, "Tentativa de conexão iniciada")
        } catch (e: Exception) {
            Log.e(appTag, "Erro ao tentar conectar: ${e.message}")
            txtStatus.text = "Erro ao conectar: ${e.message}"
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 0) {
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                permissionGranted = true
                connectToHealthService()
            } else {
                Toast.makeText(this, "Permissão negada", Toast.LENGTH_LONG).show()
                txtStatus.text = "Permissão negada - necessária para funcionar"
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        healthTrackingService?.disconnectService()
    }
} 