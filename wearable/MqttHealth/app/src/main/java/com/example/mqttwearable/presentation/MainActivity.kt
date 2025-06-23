/* While this template provides a good starting point for using Wear Compose, you can always
 * take a look at https://github.com/android/wear-os-samples/tree/main/ComposeStarter to find the
 * most up to date changes to the libraries and their usages.
 */

package com.example.mqttwearable.presentation

import android.annotation.SuppressLint
import android.app.NotificationChannel
import android.app.NotificationManager
import android.view.WindowManager

import android.content.Context
import android.content.Intent
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.view.GestureDetector
import android.view.MotionEvent
import android.view.View
import android.os.Build
import android.os.Bundle
import android.os.Vibrator
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.compose.ui.platform.LocalContext

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.wear.compose.material.MaterialTheme
import androidx.wear.compose.material.Text
import androidx.wear.compose.material.TimeText
import androidx.wear.tooling.preview.devices.WearDevices
import androidx.compose.runtime.mutableStateOf
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Spacer
import androidx.wear.compose.material.Button
import androidx.compose.foundation.layout.height
import androidx.compose.ui.unit.dp
import android.util.Log
import androidx.wear.compose.material.ButtonDefaults
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import org.eclipse.paho.client.mqttv3.MqttClient
import org.eclipse.paho.client.mqttv3.MqttConnectOptions
import org.eclipse.paho.client.mqttv3.MqttMessage
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import androidx.compose.runtime.remember
import androidx.health.services.client.data.DataType
import androidx.health.services.client.data.DeltaDataType
import androidx.lifecycle.lifecycleScope
import com.example.mqttwearable.R
import com.example.mqttwearable.mqtt.MqttHandler
import com.example.mqttwearable.health.HealthPublisher
import androidx.activity.result.contract.ActivityResultContracts.RequestMultiplePermissions
import androidx.activity.result.ActivityResultLauncher
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.example.mqttwearable.health.HealthForegroundService
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.text.InputFilter
import android.provider.Settings
import com.example.mqttwearable.data.DeviceIdManager
import com.example.mqttwearable.sensors.FallDetector
import com.example.mqttwearable.location.LocationManager
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone


class MainActivity : ComponentActivity(), SensorEventListener {

    private lateinit var mqttHandler: MqttHandler
    private lateinit var healthPublisher: HealthPublisher

    // Indica se o MQTT está conectado
    private var mqttConnected by mutableStateOf(false)

    private val requiredPermissions = arrayOf(
        android.Manifest.permission.ACTIVITY_RECOGNITION,
        android.Manifest.permission.BODY_SENSORS,
        android.Manifest.permission.ACCESS_FINE_LOCATION,
        android.Manifest.permission.ACCESS_COARSE_LOCATION,
        android.Manifest.permission.POST_NOTIFICATIONS
    )

    // 2) Crie o launcher que vai pedir essas permissões
    private lateinit var permissionsLauncher: ActivityResultLauncher<Array<String>>

    // Detector de gestos para capturar o swipe down
    private lateinit var gestureDetector: GestureDetector

    // Sensores e detecção de queda
    private lateinit var sensorManager: SensorManager
    private var accelerometer: Sensor? = null
    private lateinit var fallDetector: FallDetector
    private lateinit var vibrator: Vibrator
    private lateinit var locationManager: LocationManager
    private var currentLatitude: Double? = null
    private var currentLongitude: Double? = null
    private var fallDetectionActive = false

    // Variáveis removidas - publicação do acelerômetro agora é feita pelo HealthForegroundService

    private val spO2MeasurementDuration = 35000L
    private val spO2MeasurementInterval = 60000L
    private val isSpO2MeasurementRunning = java.util.concurrent.atomic.AtomicBoolean(false)
    private lateinit var measurementHandler: android.os.Handler
    private var connectionManagerSpO2: com.example.mqttwearable.sensors.ConnectionManager? = null
    private var spO2Listener: com.example.mqttwearable.sensors.SpO2Listener? = null
    private var previousSpO2Status: Int = com.example.mqttwearable.sensors.SpO2Status.INITIAL_STATUS

    private lateinit var txtSpO2Main: android.widget.TextView

    // Listener para receber atualizações do SpO2DataManager
    private val spO2DataListener = object : com.example.mqttwearable.data.SpO2DataManager.SpO2DataListener {
        override fun onSpO2ValueUpdated(spO2Value: Int, timestamp: Long) {
            runOnUiThread {
                txtSpO2Main.text = spO2Value.toString()
            }
        }
    }

    // Observer de conexão com o serviço de saúde
    private val spO2ConnectionObserver = object : com.example.mqttwearable.sensors.ConnectionObserver {
        override fun onConnectionResult(message: String) {
            // Se a mensagem indicar erro de suporte, ignoramos
            if (message.contains("não suportado")) return

            // Inicializar listeners quando conectado
            spO2Listener = com.example.mqttwearable.sensors.SpO2Listener { status, spO2Value ->
                onSpO2TrackerDataChanged(status, spO2Value)
            }
            connectionManagerSpO2?.initSpO2(spO2Listener!!)
            // Iniciar o loop de medição periódica
            startPeriodicSpO2Measurement()
        }

        override fun onError(exception: com.samsung.android.service.health.tracking.HealthTrackerException) {
            // Loga o erro, mas não interrompe a aplicação principal
            android.util.Log.e("MainActivity", "Erro de conexão SpO2: ${exception.message}")
        }
    }

    private fun onSpO2TrackerDataChanged(status: Int, spO2Value: Int) {
        if (status == previousSpO2Status) return
        previousSpO2Status = status

        if (status == com.example.mqttwearable.sensors.SpO2Status.MEASUREMENT_COMPLETED) {
            isSpO2MeasurementRunning.set(false)
            spO2Listener?.stopTracker()
            com.example.mqttwearable.data.SpO2DataManager.updateSpO2Value(spO2Value)
            // Voltar fundo para padrão após medição bem-sucedida
            txtSpO2Main.setBackgroundColor(resources.getColor(android.R.color.background_dark, theme))
            txtSpO2Main.setTextColor(android.graphics.Color.WHITE)
        } else if (status == com.example.mqttwearable.sensors.SpO2Status.DEVICE_MOVING ||
             status == com.example.mqttwearable.sensors.SpO2Status.LOW_SIGNAL) {
            // Erro durante medição
            txtSpO2Main.setBackgroundColor(android.graphics.Color.RED)
            txtSpO2Main.setTextColor(android.graphics.Color.WHITE)
        }
    }

    private fun performSpO2Measurement() {
        if (isSpO2MeasurementRunning.get()) return
        spO2Listener?.let {
            previousSpO2Status = com.example.mqttwearable.sensors.SpO2Status.INITIAL_STATUS
            it.startTracker()
            isSpO2MeasurementRunning.set(true)
            // Alterar fundo para AZUL enquanto mede
            txtSpO2Main.setBackgroundColor(android.graphics.Color.BLUE)
            txtSpO2Main.setTextColor(android.graphics.Color.WHITE)
            // Forçar parada de segurança após a duração prevista
            measurementHandler.postDelayed({
                if (isSpO2MeasurementRunning.get()) {
                    it.stopTracker()
                    isSpO2MeasurementRunning.set(false)
                    // Medição não concluiu – marcar como erro
                    txtSpO2Main.setBackgroundColor(android.graphics.Color.RED)
                    txtSpO2Main.setTextColor(android.graphics.Color.WHITE)
                }
            }, spO2MeasurementDuration + 2000)
        }
    }

    private fun startPeriodicSpO2Measurement() {
        measurementHandler.post(object : Runnable {
            override fun run() {
                performSpO2Measurement()
                measurementHandler.postDelayed(this, spO2MeasurementInterval)
            }
        })
    }

//    val activeTypes: Set<DeltaDataType<*, *>> = setOf(
////        DataType.STEPS,     // é um DeltaDataType<Int, SampleDataPoint<Int>>
////        DataType.CALORIES,  // é um DeltaDataType<Float, SampleDataPoint<Float>>
////        DataType.DISTANCE,   // é um DeltaDataType<Float, SampleDataPoint<Float>>
//        DataType.PACE,   // é um DeltaDataType<Float, SampleDataPoint<Float>>
//        DataType.HEART_RATE_BPM
////        DataType.ABSOLUTE_ELEVATION
//    )



    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()

        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        // Inicializar o DeviceIdManager
        DeviceIdManager.initializeDeviceId(this)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationManagerCompat.from(this).createNotificationChannel(
                NotificationChannel(
                    HealthForegroundService.CHANNEL_ID,
                    "Serviço de Saúde",
                    NotificationManager.IMPORTANCE_LOW
                )
            )
        }

        setTheme(android.R.style.Theme_DeviceDefault)

        mqttHandler = MqttHandler(applicationContext)
        healthPublisher = HealthPublisher(applicationContext, mqttHandler)

        setContentView(R.layout.activity_main)

        // Configurar detector de gestos
        setupGestureDetector()
        
        // Configurar detecção de queda
        setupFallDetection()

        val txtAndroidId = findViewById<TextView>(R.id.txtAndroidId)
        val edtIp = findViewById<EditText>(R.id.edtIp)
        val btnConectar = findViewById<Button>(R.id.btnConectar)
        val btnAcc = findViewById<Button>(R.id.btnAcc)
        val btnSpO2 = findViewById<Button>(R.id.btnSpO2)
        val txtStatus = findViewById<TextView?>(R.id.txtStatus)
        txtSpO2Main = findViewById(R.id.txtSpO2Main)

        // Inicializa o handler para medições periódicas
        measurementHandler = android.os.Handler(android.os.Looper.getMainLooper())

        // Registrar listener de dados de SpO2
        com.example.mqttwearable.data.SpO2DataManager.addListener(spO2DataListener)

        // Criar ConnectionManager para SpO2
        connectionManagerSpO2 = com.example.mqttwearable.sensors.ConnectionManager(spO2ConnectionObserver)
        connectionManagerSpO2?.connect(applicationContext)
        
        // Obter e exibir o ANDROID_ID usando o DeviceIdManager
        txtAndroidId.text = DeviceIdManager.getDeviceId()
        
        // Carregar IP do cache e definir no campo
        loadCachedIpAddress(edtIp)
        
        txtStatus?.text = "Desconectado"
        var isConnected = false
        btnConectar.text = "Conectar"

        btnConectar.setOnClickListener {
            if (!isConnected) {
                val ipText = edtIp.text.toString().trim()
                if (ipText.isEmpty()) {
                    txtStatus?.text = "Por favor, insira o IP do broker MQTT."
                    return@setOnClickListener
                }
                
                // Salvar IP no cache imediatamente
                saveCurrentIpToCache(ipText)
                
                permissionsLauncher.launch(requiredPermissions)
            } else {
                mqttHandler.disconnect()
                isConnected = false
                mqttConnected = false
                btnConectar.text = "Conectar"
                txtStatus?.text = "Desconectado"
                // Parar detecção de queda e publicação do acelerômetro quando desconectar
                stopFallDetection()
            }
        }

        btnAcc.setOnClickListener {
            // Navegar para a tela de acelerômetro
            val intent = Intent(this, AccelerometerActivity::class.java)
            // Passar o IP do broker MQTT se estiver conectado
            val ipText = edtIp.text.toString().trim()
            if (ipText.isNotEmpty()) {
                intent.putExtra("BROKER_IP", ipText)
            }
            startActivity(intent)
        }

        btnSpO2.setOnClickListener {
            // Navegar para a tela de SpO2
            val intent = Intent(this, SpO2Activity::class.java)
            startActivity(intent)
        }

        permissionsLauncher = registerForActivityResult(RequestMultiplePermissions()) { results ->
            if (results.values.all { it }) {
                val ipText = edtIp.text.toString().trim()
                if (ipText.isEmpty()) {
                    txtStatus?.text = "Por favor, insira o IP do broker MQTT."
                    return@registerForActivityResult
                }
                val brokerUrl = "tcp://$ipText:1883"
                mqttHandler.connect(
                    brokerUrl = brokerUrl,
                    clientId = "wearable-${System.currentTimeMillis()}"
                ) { success ->
                    mqttConnected = success
                    isConnected = success
                    runOnUiThread {
                        if (success) {
                            btnConectar.text = "Desconectar"
                            txtStatus?.text = "MQTT conectado - Detecção ativa"
                            // Iniciar detecção de queda quando conectado
                            startFallDetection()
                        } else {
                            btnConectar.text = "Conectar"
                            txtStatus?.text = "Falha ao conectar MQTT"
                        }
                    }
                    if (success) {
                        Log.d("MainActivity", "MQTT conectado com sucesso")
                        lifecycleScope.launch {
                            healthPublisher.startPassiveMeasure()
                        }
                        val intent = Intent(this, HealthForegroundService::class.java)
                        intent.putExtra(HealthForegroundService.EXTRA_BROKER_IP, ipText)
                        ContextCompat.startForegroundService(this, intent)
                    } else {
                        Log.e("MainActivity", "Falha ao conectar MQTT")
                    }
                }
            } else {
                Log.e("MainActivity", "Permissões de Health Services não concedidas")
            }
        }
    }

    private fun setupFallDetection() {
        // Configurar SensorManager
        sensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        accelerometer = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
        
        // Inicializar componentes
        vibrator = getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
        locationManager = LocationManager(applicationContext)
        
        // Configurar listener de localização
        locationManager.setLocationUpdateListener(object : LocationManager.LocationUpdateListener {
            override fun onLocationUpdate(latitude: Double, longitude: Double) {
                currentLatitude = latitude
                currentLongitude = longitude
                Log.d("MainActivity", "GPS: $latitude, $longitude")
            }
            
            override fun onLocationError(error: String) {
                Log.e("MainActivity", "GPS Erro: $error")
            }
        })
        
        // Iniciar atualizações de localização
        locationManager.startLocationUpdates()
        
        // Configurar detector de queda
        fallDetector = FallDetector()
        fallDetector.setFallDetectionListener(object : FallDetector.FallDetectionListener {
            override fun onFallDetected() {
                runOnUiThread {
                    if (mqttConnected) {
                        openEmergencyAlert()
                    }
                }
            }
            
            override fun onStateChanged(state: String, magnitude: Float) {
                // Log para debug
                Log.d("MainActivity", "FallDetector: $state - Magnitude: $magnitude")
            }
        })
        
        Log.d("MainActivity", "Fall detection setup completed - Nota: Detecção principal agora é no HealthForegroundService")
    }
    
    private fun startFallDetection() {
        if (accelerometer != null && !fallDetectionActive) {
            sensorManager.registerListener(this, accelerometer, SensorManager.SENSOR_DELAY_UI)
            fallDetectionActive = true
            Log.d("MainActivity", "Fall detection started - Detecção principal é no HealthForegroundService")
            
            // Nota: A detecção principal de queda e publicação do acelerômetro agora são feitas pelo HealthForegroundService
        }
    }
    
    private fun stopFallDetection() {
        if (fallDetectionActive) {
            sensorManager.unregisterListener(this)
            fallDetectionActive = false
            Log.d("MainActivity", "Fall detection stopped")
        }
    }
    
    private fun openEmergencyAlert() {
        val intent = Intent(this, EmergencyAlertActivity::class.java)
        intent.putExtra("CURRENT_LATITUDE", currentLatitude)
        intent.putExtra("CURRENT_LONGITUDE", currentLongitude)
        startActivity(intent)
    }
    
    private fun loadCachedIpAddress(edtIp: EditText) {
        val cachedBrokerUrl = mqttHandler.getCachedBrokerUrl()
        // Extrair apenas o IP do formato tcp://IP:1883
        val ipFromCache = cachedBrokerUrl.replace("tcp://", "").replace(":1883", "")
        
        Log.d("MainActivity", "Cached broker URL: $cachedBrokerUrl")
        Log.d("MainActivity", "Extracted IP: $ipFromCache")
        
        // Sempre carregar o IP do cache, mesmo se for o padrão
        if (ipFromCache.isNotEmpty() && ipFromCache != "null") {
            edtIp.setText(ipFromCache)
            Log.d("MainActivity", "IP loaded from cache: $ipFromCache")
        } else {
            Log.d("MainActivity", "No valid IP in cache, field will remain with hint")
        }
    }
    
    private fun saveCurrentIpToCache(ipAddress: String) {
        val brokerUrl = "tcp://$ipAddress:1883"
        mqttHandler.saveBrokerUrl(brokerUrl)
        Log.d("MainActivity", "IP saved to cache: $ipAddress -> $brokerUrl")
    }

    override fun onSensorChanged(event: SensorEvent?) {
        event?.let { sensorEvent ->
            if (sensorEvent.sensor.type == Sensor.TYPE_ACCELEROMETER && fallDetectionActive) {
                val x = sensorEvent.values[0]
                val y = sensorEvent.values[1]
                val z = sensorEvent.values[2]
                
                // Processar dados para detecção de queda
                fallDetector.processSensorData(x, y, z)
            }
        }
    }
    
    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {
        // Não é necessário implementar para este caso de uso
    }


    override fun onStart() {
        super.onStart()

        permissionsLauncher.launch(requiredPermissions)

    }

    @SuppressLint("ImplicitSamInstance")
    override fun onStop() {
        super.onStop()
    }

    // Métodos de publicação do acelerômetro removidos - agora são feitos pelo HealthForegroundService

    override fun onDestroy() {
        super.onDestroy()
        stopFallDetection()
        locationManager.stopLocationUpdates()
        // Limpar medições de SpO2
        measurementHandler.removeCallbacksAndMessages(null)
        com.example.mqttwearable.data.SpO2DataManager.removeListener(spO2DataListener)
        spO2Listener?.stopTracker()
        connectionManagerSpO2?.disconnect()
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
                        if (diffY > 0) {
                            // Swipe para baixo - abrir tela de acelerômetro
                            onSwipeDown()
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

    private fun onSwipeDown() {
        // Navegar para a tela de acelerômetro
        val intent = Intent(this, AccelerometerActivity::class.java)
        // Passar o IP do broker MQTT se estiver conectado
        val edtIp = findViewById<EditText>(R.id.edtIp)
        val ipText = edtIp.text.toString().trim()
        if (ipText.isNotEmpty()) {
            intent.putExtra("BROKER_IP", ipText)
        }
        startActivity(intent)
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        return gestureDetector.onTouchEvent(event) || super.onTouchEvent(event)
    }
}