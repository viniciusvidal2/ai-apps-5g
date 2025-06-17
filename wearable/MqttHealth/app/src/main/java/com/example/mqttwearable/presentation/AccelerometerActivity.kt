package com.example.mqttwearable.presentation

import android.annotation.SuppressLint
import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.Vibrator
import android.view.GestureDetector
import android.view.MotionEvent
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import androidx.activity.ComponentActivity
import com.example.mqttwearable.R
import com.example.mqttwearable.sensors.FallDetector
import com.example.mqttwearable.mqtt.MqttHandler
import com.example.mqttwearable.location.LocationManager
import com.example.mqttwearable.data.DeviceIdManager
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

class AccelerometerActivity : ComponentActivity(), SensorEventListener {
    
    private lateinit var sensorManager: SensorManager
    private var accelerometer: Sensor? = null
    private var gyroscope: Sensor? = null
    private var magnetometer: Sensor? = null
    private var linearAccelerometer: Sensor? = null
    private var rotationVector: Sensor? = null
    
    private lateinit var txtAccelerometer: TextView
    private lateinit var txtGyroscope: TextView
    private lateinit var txtMagnetometer: TextView
    private lateinit var txtLinearAccel: TextView
    private lateinit var txtRotationVector: TextView
    private lateinit var txtStatus: TextView
    private lateinit var txtFallStatus: TextView
    private lateinit var btnVoltar: Button
    private lateinit var layoutFallAlert: LinearLayout
    private lateinit var txtCountdown: TextView
    private lateinit var btnCancelAlert: Button
    private lateinit var txtDebugInfo: TextView
    private lateinit var layoutFallAlertOverlay: LinearLayout
    private lateinit var txtCountdownBig: TextView
    private lateinit var btnCancelFallAlert: Button
    
    // Detector de gestos para capturar o swipe up
    private lateinit var gestureDetector: GestureDetector
    
    // Detector de queda e componentes relacionados
    private lateinit var fallDetector: FallDetector
    private lateinit var vibrator: Vibrator
    private lateinit var mqttHandler: MqttHandler
    private lateinit var locationManager: LocationManager
    private var alertHandler: Handler? = null
    private var alertCountdown = 10 // Alterado de 5 para 10 segundos
    private var isAlertActive = false
    private var brokerIp: String? = null
    
    // Localização atual
    private var currentLatitude: Double? = null
    private var currentLongitude: Double? = null

    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_accelerometer)
        
        // Inicializar o DeviceIdManager
        DeviceIdManager.initializeDeviceId(this)
        
        // Receber o IP do broker MQTT via Intent
        brokerIp = intent.getStringExtra("BROKER_IP")
        
        // Inicializar os TextViews
        txtAccelerometer = findViewById(R.id.txtAccelerometer)
        txtGyroscope = findViewById(R.id.txtGyroscope)
        txtMagnetometer = findViewById(R.id.txtMagnetometer)
        txtLinearAccel = findViewById(R.id.txtLinearAccel)
        txtRotationVector = findViewById(R.id.txtRotationVector)
        txtStatus = findViewById(R.id.txtSensorStatus)
        txtFallStatus = findViewById(R.id.txtFallStatus)
        btnVoltar = findViewById(R.id.btnVoltar)
        layoutFallAlert = findViewById(R.id.layoutFallAlert)
        txtCountdown = findViewById(R.id.txtCountdown)
        btnCancelAlert = findViewById(R.id.btnCancelAlert)
        txtDebugInfo = findViewById(R.id.txtDebugInfo)
        layoutFallAlertOverlay = findViewById(R.id.layoutFallAlertOverlay)
        txtCountdownBig = findViewById(R.id.txtCountdownBig)
        btnCancelFallAlert = findViewById(R.id.btnCancelFallAlert)
        
        // Configurar SensorManager
        sensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        
        // Obter sensores
        accelerometer = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
        gyroscope = sensorManager.getDefaultSensor(Sensor.TYPE_GYROSCOPE)
        magnetometer = sensorManager.getDefaultSensor(Sensor.TYPE_MAGNETIC_FIELD)
        linearAccelerometer = sensorManager.getDefaultSensor(Sensor.TYPE_LINEAR_ACCELERATION)
        rotationVector = sensorManager.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR)
        
        // Verificar quais sensores estão disponíveis
        updateSensorStatus()
        
        // Configurar detector de gestos
        setupGestureDetector()
        
        // Configurar botão voltar
        btnVoltar.setOnClickListener {
            finish()
        }
        
        // Configurar componentes do detector de queda
        setupFallDetection()
    }
    
    private fun updateSensorStatus() {
        val availableSensors = mutableListOf<String>()
        
        if (accelerometer != null) availableSensors.add("Acelerômetro")
        if (gyroscope != null) availableSensors.add("Giroscópio")
        if (magnetometer != null) availableSensors.add("Magnetômetro")
        if (linearAccelerometer != null) availableSensors.add("Acelerômetro Linear")
        if (rotationVector != null) availableSensors.add("Vetor Rotação")
        
        txtStatus.text = "Sensores disponíveis: ${availableSensors.joinToString(", ")}"
    }
    
    override fun onResume() {
        super.onResume()
        
        // Registrar listeners para todos os sensores disponíveis
        accelerometer?.let {
            sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_UI)
        }
        
        gyroscope?.let {
            sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_UI)
        }
        
        magnetometer?.let {
            sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_UI)
        }
        
        linearAccelerometer?.let {
            sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_UI)
        }
        
        rotationVector?.let {
            sensorManager.registerListener(this, it, SensorManager.SENSOR_DELAY_UI)
        }
    }
    
    override fun onPause() {
        super.onPause()
        sensorManager.unregisterListener(this)
    }
    
    override fun onDestroy() {
        super.onDestroy()
        // Limpar recursos do detector de queda
        if (isAlertActive) {
            cancelFallAlert()
        }
        alertHandler?.removeCallbacksAndMessages(null)
        locationManager.stopLocationUpdates()
    }
    
    @SuppressLint("DefaultLocale")
    override fun onSensorChanged(event: SensorEvent?) {
        event?.let { sensorEvent ->
            when (sensorEvent.sensor.type) {
                Sensor.TYPE_ACCELEROMETER -> {
                    val x = sensorEvent.values[0]
                    val y = sensorEvent.values[1]
                    val z = sensorEvent.values[2]
                    
                    txtAccelerometer.text = "Acelerômetro:\nX: ${String.format("%.2f", x)}\nY: ${String.format("%.2f", y)}\nZ: ${String.format("%.2f", z)}"
                    
                    // Processar dados para detecção de queda (apenas se não estiver em alerta)
                    if (!isAlertActive) {
                        fallDetector.processSensorData(x, y, z)
                        
                        // Atualizar status do detector
                        val detectionState = fallDetector.getDetectionState()
                        txtFallStatus.text = "Detector de Queda: $detectionState"
                        
                        // Mudar cor do status baseado no estado
                        if (fallDetector.isCurrentlyDetecting()) {
                            txtFallStatus.setBackgroundColor(getColor(android.R.color.holo_orange_dark))
                        } else {
                            txtFallStatus.setBackgroundColor(getColor(android.R.color.darker_gray))
                        }
                    }
                }
                
                Sensor.TYPE_GYROSCOPE -> {
                    txtGyroscope.text = "Giroscópio:\nX: ${String.format("%.2f", sensorEvent.values[0])}\nY: ${String.format("%.2f", sensorEvent.values[1])}\nZ: ${String.format("%.2f", sensorEvent.values[2])}"
                }
                
                Sensor.TYPE_MAGNETIC_FIELD -> {
                    txtMagnetometer.text = "Magnetômetro:\nX: ${String.format("%.2f", sensorEvent.values[0])}\nY: ${String.format("%.2f", sensorEvent.values[1])}\nZ: ${String.format("%.2f", sensorEvent.values[2])}"
                }
                
                Sensor.TYPE_LINEAR_ACCELERATION -> {
                    txtLinearAccel.text = "Aceleração Linear:\nX: ${String.format("%.2f", sensorEvent.values[0])}\nY: ${String.format("%.2f", sensorEvent.values[1])}\nZ: ${String.format("%.2f", sensorEvent.values[2])}"
                }
                
                Sensor.TYPE_ROTATION_VECTOR -> {
                    val values = if (sensorEvent.values.size >= 4) {
                        "Vetor Rotação:\nX: ${String.format("%.2f", sensorEvent.values[0])}\nY: ${String.format("%.2f", sensorEvent.values[1])}\nZ: ${String.format("%.2f", sensorEvent.values[2])}\nW: ${String.format("%.2f", sensorEvent.values[3])}"
                    } else {
                        "Vetor Rotação:\nX: ${String.format("%.2f", sensorEvent.values[0])}\nY: ${String.format("%.2f", sensorEvent.values[1])}\nZ: ${String.format("%.2f", sensorEvent.values[2])}"
                    }
                    txtRotationVector.text = values
                }
            }
        }
    }
    
    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {
        // Não é necessário implementar para este caso de uso
    }

    private fun setupGestureDetector() {
        gestureDetector = GestureDetector(this, object : GestureDetector.SimpleOnGestureListener() {
            private val SWIPE_THRESHOLD = 100
            private val SWIPE_VELOCITY_THRESHOLD = 100

            override fun onFling(
                e1: MotionEvent?,
                e2: MotionEvent,
                velocityX: Float,
                velocityY: Float
            ): Boolean {
                // Não processar gestos se o alerta estiver ativo
                if (isAlertActive) return false
                
                if (e1 == null) return false
                
                val diffY = e2.y - e1.y
                val diffX = e2.x - e1.x
                
                if (Math.abs(diffY) > Math.abs(diffX)) {
                    if (Math.abs(diffY) > SWIPE_THRESHOLD && Math.abs(velocityY) > SWIPE_VELOCITY_THRESHOLD) {
                        if (diffY < 0) {
                            // Swipe para cima - voltar para tela principal
                            onSwipeUp()
                            return true
                        }
                    }
                }
                return false
            }
        })

        // Aplicar o detector de gestos à view raiz
        findViewById<View>(android.R.id.content).setOnTouchListener { _, event ->
            // Não processar toques se o alerta estiver ativo
            if (isAlertActive) {
                false
            } else {
                gestureDetector.onTouchEvent(event)
            }
        }
    }

    private fun onSwipeUp() {
        // Voltar para a tela principal
        finish()
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        // Se o alerta estiver ativo, permitir toques normais (para o botão funcionar)
        // Caso contrário, processar gestos normalmente
        return if (isAlertActive) {
            super.onTouchEvent(event)
        } else {
            gestureDetector.onTouchEvent(event) || super.onTouchEvent(event)
        }
    }

    private fun setupFallDetection() {
        // Inicializar componentes
        vibrator = getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
        mqttHandler = MqttHandler(applicationContext)
        locationManager = LocationManager(applicationContext)
        
        // Configurar listener de localização
        locationManager.setLocationUpdateListener(object : LocationManager.LocationUpdateListener {
            override fun onLocationUpdate(latitude: Double, longitude: Double) {
                currentLatitude = latitude
                currentLongitude = longitude
                runOnUiThread {
                    txtDebugInfo.text = "${txtDebugInfo.text}\nGPS: $latitude, $longitude"
                }
            }
            
            override fun onLocationError(error: String) {
                runOnUiThread {
                    txtDebugInfo.text = "${txtDebugInfo.text}\nGPS Erro: $error"
                }
            }
        })
        
        // Iniciar atualizações de localização
        locationManager.startLocationUpdates()
        
        // Configurar detector de queda
        fallDetector = FallDetector()
        fallDetector.setFallDetectionListener(object : FallDetector.FallDetectionListener {
            override fun onFallDetected() {
                runOnUiThread {
                    startFallAlert()
                }
            }
            
            override fun onStateChanged(state: String, magnitude: Float) {
                runOnUiThread {
                    val debugText = "Magnitude: ${String.format("%.2f", magnitude)}\n${fallDetector.getDebugInfo()}"
                    txtDebugInfo.text = debugText
                }
            }
            

        })
        
        // Configurar botão de cancelar alerta
        btnCancelAlert.setOnClickListener {
            cancelFallAlert()
        }
        
        // Configurar botão de cancelar alerta na tela vermelha
        btnCancelFallAlert.setOnClickListener {
            cancelFallAlert()
        }
    }

    private fun startFallAlert() {
        if (isAlertActive) return
        
        isAlertActive = true
        alertCountdown = 10 // Alterado de 5 para 10 segundos
        
        // Mostrar tela vermelha completa
        layoutFallAlertOverlay.visibility = View.VISIBLE
        txtCountdownBig.text = alertCountdown.toString()
        
        // Iniciar vibração e countdown
        startVibrationAndCountdown()
    }

    private fun startVibrationAndCountdown() {
        alertHandler = Handler(Looper.getMainLooper())
        
        val vibrationRunnable = object : Runnable {
            override fun run() {
                if (isAlertActive && alertCountdown > 0) {
                    // Vibrar
                    if (vibrator.hasVibrator()) {
                        vibrator.vibrate(500) // Vibra por 500ms
                    }
                    
                    // Atualizar countdown na tela vermelha
                    txtCountdownBig.text = alertCountdown.toString()
                    alertCountdown--
                    
                    // Agendar próxima vibração
                    alertHandler?.postDelayed(this, 1000)
                } else if (isAlertActive && alertCountdown <= 0) {
                    // Tempo esgotado - enviar alerta
                    sendFallAlert()
                }
            }
        }
        
        alertHandler?.post(vibrationRunnable)
    }

    private fun sendFallAlert() {
        // Criar JSON com horário atual em formato ISO 8601 UTC
        val sdf = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
        sdf.timeZone = TimeZone.getTimeZone("UTC")
        val currentTime = sdf.format(Date())
        
        // Criar JSON com Device ID, localização e dados de queda
        val fallMessage = buildString {
            append("{")
            append("\"time\":\"$currentTime\",")
            append("\"fall\":1,")
            append("\"id\":\"${DeviceIdManager.getDeviceId()}\"")
            
            // Adicionar localização se disponível
            if (currentLatitude != null && currentLongitude != null) {
                append(",\"latitude\":$currentLatitude,\"longitude\":$currentLongitude")
            }
            
            append("}")
        }
        
        // Conectar ao MQTT e enviar mensagem se o IP estiver disponível
        brokerIp?.let { ip ->
            val brokerUrl = "tcp://$ip:1883"
            mqttHandler.connect(brokerUrl, "fall-alert-${System.currentTimeMillis()}") { connected ->
                if (connected) {
                    // Enviar mensagem MQTT para o tópico /fall
                    mqttHandler.publish("/fall", fallMessage) { success ->
                        runOnUiThread {
                            if (success) {
                                txtFallStatus.text = "Alerta de Queda ENVIADO!"
                            } else {
                                txtFallStatus.text = "Erro ao enviar alerta!"
                            }
                            txtFallStatus.setBackgroundColor(getColor(android.R.color.holo_red_dark))
                        }
                    }
                } else {
                    runOnUiThread {
                        txtFallStatus.text = "Erro de conexão MQTT!"
                        txtFallStatus.setBackgroundColor(getColor(android.R.color.holo_red_dark))
                    }
                }
            }
        } ?: run {
            // Se não há IP, apenas mostrar mensagem
            txtFallStatus.text = "Alerta criado (sem conexão MQTT)"
            txtFallStatus.setBackgroundColor(getColor(android.R.color.holo_red_dark))
        }
        
        // Esconder tela vermelha
        layoutFallAlertOverlay.visibility = View.GONE
        isAlertActive = false
        
        // Parar vibração
        vibrator.cancel()
    }

    private fun cancelFallAlert() {
        isAlertActive = false
        alertHandler?.removeCallbacksAndMessages(null)
        
        // Esconder tela vermelha
        layoutFallAlertOverlay.visibility = View.GONE
        
        // Parar vibração
        vibrator.cancel()
        
        // Atualizar status
        txtFallStatus.text = "Alerta CANCELADO - Monitorando"
        txtFallStatus.setBackgroundColor(getColor(android.R.color.darker_gray))
    }
    

} 