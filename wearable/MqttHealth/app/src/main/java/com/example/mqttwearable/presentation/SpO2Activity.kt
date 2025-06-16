package com.example.mqttwearable.presentation

import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.CountDownTimer
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.WindowManager
import android.widget.Button
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.core.app.ActivityCompat
import com.example.mqttwearable.R
import com.example.mqttwearable.sensors.*
import com.samsung.android.service.health.tracking.HealthTrackerException
import java.util.concurrent.atomic.AtomicBoolean

class SpO2Activity : Activity() {

    private val appTag = "SpO2Activity"
    private val measurementDuration = 35000L
    private val measurementTick = 250L
    
    private val isMeasurementRunning = AtomicBoolean(false)
    private var uiUpdateThread: Thread? = null
    private var connectionManager: ConnectionManager? = null
    private var heartRateListener: HeartRateListener? = null
    private var spO2Listener: SpO2Listener? = null
    private var connected = false
    private var permissionGranted = false
    private var previousStatus = SpO2Status.INITIAL_STATUS
    private var heartRateDataLast = HeartRateData()
    
    private lateinit var txtHeartRate: TextView
    private lateinit var txtStatus: TextView
    private lateinit var txtSpO2: TextView
    private lateinit var butStart: Button
    private lateinit var btnBack: Button
    private lateinit var progressBar: ProgressBar
    
    private val countDownTimer = object : CountDownTimer(measurementDuration, measurementTick) {
        override fun onTick(timeLeft: Long) {
            if (isMeasurementRunning.get()) {
                runOnUiThread {
                    progressBar.progress = progressBar.progress + 1
                }
            } else {
                cancel()
            }
        }
        
        override fun onFinish() {
            if (!isMeasurementRunning.get()) return
            Log.i(appTag, "Failed measurement")
            spO2Listener?.stopTracker()
            isMeasurementRunning.set(false)
            runOnUiThread {
                txtStatus.text = "Medição falhou"
                txtSpO2.text = "0"
                butStart.text = "Medir"
                progressBar.progress = progressBar.max
            }
            window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
    }
    
    private fun onHeartRateTrackerDataChanged(hrData: HeartRateData) {
        runOnUiThread {
            heartRateDataLast = hrData
            Log.i(appTag, "HR Status: ${hrData.status}")
            if (hrData.status == HeartRateStatus.HR_STATUS_FIND_HR) {
                txtHeartRate.text = hrData.hr.toString()
                Log.i(appTag, "HR: ${hrData.hr}")
            } else {
                txtHeartRate.text = "0"
            }
        }
    }
    
    private fun onSpO2TrackerDataChanged(status: Int, spO2Value: Int) {
        if (status == previousStatus) return
        previousStatus = status
        
        when (status) {
            SpO2Status.CALCULATING -> {
                Log.i(appTag, "Calculating measurement")
                runOnUiThread {
                    txtStatus.text = "Calculando..."
                }
            }
            SpO2Status.DEVICE_MOVING -> {
                Log.i(appTag, "Device is moving")
                runOnUiThread {
                    Toast.makeText(applicationContext, "Dispositivo em movimento.", Toast.LENGTH_SHORT).show()
                }
            }
            SpO2Status.LOW_SIGNAL -> {
                Log.i(appTag, "Low signal quality")
                runOnUiThread {
                    Toast.makeText(applicationContext, "Qualidade de sinal baixa.", Toast.LENGTH_SHORT).show()
                }
            }
            SpO2Status.MEASUREMENT_COMPLETED -> {
                Log.i(appTag, "Measurement completed")
                isMeasurementRunning.set(false)
                spO2Listener?.stopTracker()
                runOnUiThread {
                    txtStatus.text = "Medição concluída."
                    txtSpO2.text = spO2Value.toString()
                    butStart.text = "Medir"
                    progressBar.progress = progressBar.max
                }
                window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            }
        }
    }
    
    private fun onError(errorMessage: String) {
        runOnUiThread {
            Toast.makeText(applicationContext, errorMessage, Toast.LENGTH_LONG).show()
        }
        countDownTimer.onFinish()
    }
    
    private val connectionObserver = object : ConnectionObserver {
        override fun onConnectionResult(message: String) {
            runOnUiThread {
                Toast.makeText(applicationContext, message, Toast.LENGTH_LONG).show()
            }
            
            if (message.contains("não suportado")) {
                finish()
                return
            }
            
            connected = true
            
            spO2Listener = SpO2Listener { status, spO2Value ->
                onSpO2TrackerDataChanged(status, spO2Value)
            }
            
            heartRateListener = HeartRateListener { hrData ->
                onHeartRateTrackerDataChanged(hrData)
            }
            
            connectionManager?.initSpO2(spO2Listener!!)
            connectionManager?.initHeartRate(heartRateListener!!)
            
            heartRateListener?.startTracker()
        }
        
        override fun onError(exception: HealthTrackerException) {
            if (exception.errorCode == HealthTrackerException.OLD_PLATFORM_VERSION || 
                exception.errorCode == HealthTrackerException.PACKAGE_NOT_INSTALLED) {
                runOnUiThread {
                    Toast.makeText(applicationContext, "Versão da Plataforma de Saúde está desatualizada", Toast.LENGTH_LONG).show()
                }
            }
            if (exception.hasResolution()) {
                exception.resolve(this@SpO2Activity)
            } else {
                runOnUiThread {
                    Toast.makeText(applicationContext, "Erro de conexão", Toast.LENGTH_LONG).show()
                }
                Log.e(appTag, "Could not connect to Health Tracking Service: ${exception.message}")
            }
            finish()
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
            createConnectionManager()
        }
    }
    
    private fun initializeViews() {
        txtHeartRate = findViewById(R.id.txtHeartRate)
        txtStatus = findViewById(R.id.txtStatus)
        txtSpO2 = findViewById(R.id.txtSpO2)
        butStart = findViewById(R.id.butStart)
        btnBack = findViewById(R.id.btnBack)
        progressBar = findViewById(R.id.progressBar)
        
        adjustProgressBar()
    }
    
    private fun setupClickListeners() {
        butStart.setOnClickListener {
            performMeasurement()
        }
        
        btnBack.setOnClickListener {
            finish()
        }
    }
    
    private fun adjustProgressBar() {
        progressBar.max = (measurementDuration / measurementTick).toInt()
        progressBar.progress = 0
    }
    
    private fun performMeasurement() {
        if (isPermissionsOrConnectionInvalid()) return
        
        if (!isMeasurementRunning.get()) {
            previousStatus = SpO2Status.INITIAL_STATUS
            butStart.text = "Parar"
            txtSpO2.text = "0"
            progressBar.progress = 0
            window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            spO2Listener?.startTracker()
            isMeasurementRunning.set(true)
            uiUpdateThread = Thread { countDownTimer.start() }
            uiUpdateThread?.start()
        } else {
            butStart.isEnabled = false
            isMeasurementRunning.set(false)
            window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            spO2Listener?.stopTracker()
            val progressHandler = Handler(Looper.getMainLooper())
            progressHandler.postDelayed({
                butStart.text = "Medir"
                txtStatus.text = "Pressione Medir para iniciar medição de SpO2."
                progressBar.progress = 0
                butStart.isEnabled = true
            }, measurementTick * 2)
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        heartRateListener?.stopTracker()
        spO2Listener?.stopTracker()
        connectionManager?.disconnect()
    }
    
    private fun createConnectionManager() {
        try {
            connectionManager = ConnectionManager(connectionObserver)
            connectionManager?.connect(applicationContext)
        } catch (t: Throwable) {
            Log.e(appTag, t.message ?: "Unknown error")
        }
    }
    
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 0) {
            permissionGranted = true
            for (i in permissions.indices) {
                if (grantResults[i] == PackageManager.PERMISSION_DENIED) {
                    if (!shouldShowRequestPermissionRationale(permissions[i])) {
                        Toast.makeText(applicationContext, "Permissões negadas permanentemente", Toast.LENGTH_LONG).show()
                    } else {
                        Toast.makeText(applicationContext, "Permissão de sensores corporais é necessária para fazer uma medição.", Toast.LENGTH_LONG).show()
                    }
                    permissionGranted = false
                    break
                }
            }
            if (permissionGranted) {
                createConnectionManager()
            }
        }
    }
    
    private fun isPermissionsOrConnectionInvalid(): Boolean {
        if (ActivityCompat.checkSelfPermission(applicationContext, Manifest.permission.BODY_SENSORS) == PackageManager.PERMISSION_DENIED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.BODY_SENSORS), 0)
        }
        if (!permissionGranted) {
            Log.i(appTag, "Could not get permissions. Terminating measurement")
            return true
        }
        if (!connected) {
            Toast.makeText(applicationContext, "Erro de conexão", Toast.LENGTH_SHORT).show()
            return true
        }
        return false
    }
} 