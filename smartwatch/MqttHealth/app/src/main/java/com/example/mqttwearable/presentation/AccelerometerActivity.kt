package com.example.mqttwearable.presentation

import android.annotation.SuppressLint
import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Bundle
import android.view.GestureDetector
import android.view.MotionEvent
import android.view.View
import android.widget.Button
import android.widget.TextView
import androidx.activity.ComponentActivity
import com.example.mqttwearable.R

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
    private lateinit var btnVoltar: Button
    
    // Detector de gestos para capturar o swipe up
    private lateinit var gestureDetector: GestureDetector
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_accelerometer)
        
        // Inicializar os TextViews
        txtAccelerometer = findViewById(R.id.txtAccelerometer)
        txtGyroscope = findViewById(R.id.txtGyroscope)
        txtMagnetometer = findViewById(R.id.txtMagnetometer)
        txtLinearAccel = findViewById(R.id.txtLinearAccel)
        txtRotationVector = findViewById(R.id.txtRotationVector)
        txtStatus = findViewById(R.id.txtSensorStatus)
        btnVoltar = findViewById(R.id.btnVoltar)
        
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
    
    @SuppressLint("DefaultLocale")
    override fun onSensorChanged(event: SensorEvent?) {
        event?.let { sensorEvent ->
            when (sensorEvent.sensor.type) {
                Sensor.TYPE_ACCELEROMETER -> {
                    txtAccelerometer.text = "Acelerômetro:\nX: ${String.format("%.2f", sensorEvent.values[0])}\nY: ${String.format("%.2f", sensorEvent.values[1])}\nZ: ${String.format("%.2f", sensorEvent.values[2])}"
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
            gestureDetector.onTouchEvent(event)
        }
    }

    private fun onSwipeUp() {
        // Voltar para a tela principal
        finish()
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        return gestureDetector.onTouchEvent(event) || super.onTouchEvent(event)
    }
} 