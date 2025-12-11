/* While this template provides a good starting point for using Wear Compose, you can always
 * take a look at https://github.com/android/wear-os-samples/tree/main/ComposeStarter to find the
 * most up to date changes to the libraries and their usages.
 */

package com.sae5g.mqttwearable.presentation

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
import kotlinx.coroutines.delay
import androidx.compose.runtime.remember
import androidx.health.services.client.data.DataType
import androidx.health.services.client.data.DeltaDataType
// lifecycleScope import removido - não usado mais na MainActivity
import com.sae5g.mqttwearable.R
import com.sae5g.mqttwearable.mqtt.MqttHandler
// HealthPublisher import removido - usado apenas no HealthForegroundService
import androidx.activity.result.contract.ActivityResultContracts.RequestMultiplePermissions
import androidx.activity.result.ActivityResultLauncher
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.sae5g.mqttwearable.health.HealthForegroundService
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.text.InputFilter
import android.provider.Settings
import com.sae5g.mqttwearable.data.DeviceIdManager
import com.sae5g.mqttwearable.sensors.FallDetector
import com.sae5g.mqttwearable.location.LocationManager
import com.sae5g.mqttwearable.connectivity.WiFiConnectivityManager
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.os.CountDownTimer
import com.sae5g.mqttwearable.config.AppConfig


class MainActivity : ComponentActivity(), SensorEventListener {

    private lateinit var mqttHandler: MqttHandler
    // healthPublisher removido - será usado apenas no HealthForegroundService

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
    private lateinit var wifiConnectivityManager: WiFiConnectivityManager
    private lateinit var connectivityManager: ConnectivityManager
    private var networkCallback: ConnectivityManager.NetworkCallback? = null
    private var currentLatitude: Double? = null
    private var currentLongitude: Double? = null
    private var fallDetectionActive = false
    
    // Timer para próximo envio MQTT
    private var mqttSendTimer: CountDownTimer? = null
    private var nextSendTime: Long = AppConfig.HEALTH_DATA_COUNTDOWN_MS // Configurado em AppConfig
    private var isWifiConnected = false
    private var currentWifiName: String? = null

    // Variáveis removidas - publicação do acelerômetro agora é feita pelo HealthForegroundService

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
        // HealthPublisher removido - será usado apenas no HealthForegroundService
        
        // Configurar timer a partir do AppConfig
        nextSendTime = AppConfig.HEALTH_DATA_COUNTDOWN_MS
        
        // Inicializar gerenciador de conectividade WiFi
        wifiConnectivityManager = WiFiConnectivityManager(applicationContext)
        connectivityManager = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        setupWifiStatusListener()
        setupNetworkMonitoring()

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
        val btnGps = findViewById<Button>(R.id.btnGps)
        val txtStatus = findViewById<TextView?>(R.id.txtStatus)
        
        // Configurar timer MQTT
        setupMqttTimer()

        // Obter e exibir o ANDROID_ID usando o DeviceIdManager
        txtAndroidId.text = DeviceIdManager.getDeviceId()
        
        // Carregar IP do cache e definir no campo
        loadCachedIpAddress(edtIp)
        
        txtStatus?.text = "Verificando WiFi..."
        var isConnected = false
        btnConectar.text = "Conectar"
        
        // O status WiFi será verificado pelo setupNetworkMonitoring()

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
                updateConnectionStatus()
                // Parar detecção de queda e publicação do acelerômetro quando desconectar
                stopFallDetection()
                stopMqttSendTimer()
            }
        }
        
        // Botão temporário para testar fila (long press no botão conectar)
        btnConectar.setOnLongClickListener {
            val queueStats = mqttHandler.getQueueStats()
            val queueSize = queueStats["totalMessages"] as? Int ?: 0
            
            Log.d("MainActivity", "🐛 TESTE MANUAL: Verificando fila...")
            Log.d("MainActivity", "🐛 TESTE MANUAL: Tamanho da fila: $queueSize")
            Log.d("MainActivity", "🐛 TESTE MANUAL: Stats completas: $queueStats")
            
            if (queueSize > 0) {
                Log.d("MainActivity", "🐛 TESTE MANUAL: Forçando processamento da fila...")
                txtStatus?.text = "Testando fila ($queueSize msgs)..."
                mqttHandler.onWiFiReconnected()
                
                // Voltar ao status normal após 3 segundos
                android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                    updateConnectionStatus()
                }, 3000)
            } else {
                txtStatus?.text = "Fila vazia para teste"
                android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                    updateConnectionStatus()
                }, 2000)
            }
            
            true // Consumir o long click
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

        btnGps.setOnClickListener {
            val intent = Intent(this, GpsStatusActivity::class.java)
            startActivity(intent)
        }

        permissionsLauncher = registerForActivityResult(RequestMultiplePermissions()) { results ->
            if (results.values.all { it }) {
                val ipText = edtIp.text.toString().trim()
                // Sempre iniciar o serviço para monitorar Bluetooth/GPS mesmo sem MQTT
                val fgIntent = Intent(this, HealthForegroundService::class.java)

                if (ipText.isEmpty()) {
                    ContextCompat.startForegroundService(this, fgIntent)
                    txtStatus?.text = "Serviço iniciado (BT/GPS) sem MQTT"
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
                            updateConnectionStatus()
                            // Iniciar detecção de queda quando conectado
                            startFallDetection()
                            // Aguardar antes de iniciar timer (sincronizar com HealthPublisher)
                            android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                                startMqttSendTimer()
                            }, AppConfig.TIMER_SYNC_DELAY_MS)
                        } else {
                            btnConectar.text = "Conectar"
                            txtStatus?.text = "Falha ao conectar MQTT"
                            stopMqttSendTimer()
                        }
                    }
                    if (success) {
                        Log.d("MainActivity", "MQTT conectado com sucesso")
                        // HealthPublisher removido da MainActivity - roda apenas no HealthForegroundService
                        fgIntent.putExtra(HealthForegroundService.EXTRA_BROKER_IP, ipText)
                        ContextCompat.startForegroundService(this, fgIntent)
                    } else {
                        Log.e("MainActivity", "Falha ao conectar MQTT")
                        // Mesmo sem MQTT, manter serviço rodando para BT/GPS
                        ContextCompat.startForegroundService(this, fgIntent)
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
    
    private fun setupWifiStatusListener() {
        wifiConnectivityManager.setStatusListener(object : WiFiConnectivityManager.WiFiStatusListener {
            override fun onWiFiStatusChanged(isConnected: Boolean, networkName: String?) {
                runOnUiThread {
                    val txtStatus = findViewById<TextView?>(R.id.txtStatus)
                    if (isConnected) {
                        txtStatus?.text = "WiFi: $networkName"
                    } else {
                        txtStatus?.text = "Sem WiFi"
                    }
                }
            }
            
            override fun onMqttServerReachable(isReachable: Boolean, serverIp: String) {
                runOnUiThread {
                    val txtStatus = findViewById<TextView?>(R.id.txtStatus)
                    if (isReachable) {
                        txtStatus?.text = "WiFi + MQTT OK"
                    } else {
                        txtStatus?.text = "WiFi OK, MQTT inacessível"
                    }
                }
            }
            
            override fun onError(message: String) {
                runOnUiThread {
                    val txtStatus = findViewById<TextView?>(R.id.txtStatus)
                    txtStatus?.text = message
                }
                Log.e("MainActivity", "WiFi Error: $message")
            }
        })
    }
    
    private fun setupNetworkMonitoring() {
        val networkRequest = NetworkRequest.Builder()
            .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
            .build()
            
        networkCallback = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                Log.d("MainActivity", "WiFi network available - tentando reconexão automática")
                CoroutineScope(Dispatchers.IO).launch {
                    // Aguardar um pouco para rede estabilizar
                    delay(2000)
                    
                    // Tentar reconectar a redes conhecidas
                    wifiConnectivityManager.attemptConnectionToKnownNetworks { success ->
                        CoroutineScope(Dispatchers.IO).launch {
                            val networkName = wifiConnectivityManager.getCurrentNetworkName()
                            val isConnected = wifiConnectivityManager.isWiFiConnected()
                            
                            runOnUiThread {
                                isWifiConnected = isConnected
                                currentWifiName = if (isConnected) networkName else null
                                updateConnectionStatus()
                                
                                if (success && isConnected) {
                                    Log.d("MainActivity", "🎉 Reconexão WiFi automática bem-sucedida: $networkName")
                                    // Processar fila de mensagens após reconexão WiFi
                                    Log.d("MainActivity", "🔄 Chamando mqttHandler.onWiFiReconnected()...")
                                    mqttHandler.onWiFiReconnected()
                                } else {
                                    Log.w("MainActivity", "❌ Falha na reconexão WiFi automática")
                                }
                            }
                        }
                    }
                }
            }
            
            override fun onLost(network: Network) {
                Log.d("MainActivity", "WiFi network lost")
                runOnUiThread {
                    isWifiConnected = false
                    currentWifiName = null
                    updateConnectionStatus()
                }
            }
            
            override fun onCapabilitiesChanged(network: Network, networkCapabilities: NetworkCapabilities) {
                // Verificar se ainda tem capacidades de internet
                val hasInternet = networkCapabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                runOnUiThread {
                    if (!hasInternet && isWifiConnected) {
                        isWifiConnected = false
                        updateConnectionStatus()
                    }
                }
            }
        }
        
        connectivityManager.registerNetworkCallback(networkRequest, networkCallback!!)
        
        // Verificar status inicial
        checkInitialWifiStatus()
    }
    
    private fun checkInitialWifiStatus() {
        CoroutineScope(Dispatchers.IO).launch {
            isWifiConnected = wifiConnectivityManager.isWiFiConnected()
            currentWifiName = wifiConnectivityManager.getCurrentNetworkName()
            
            runOnUiThread {
                updateConnectionStatus()
            }
        }
    }
    
    private fun updateConnectionStatus() {
        val txtStatus = findViewById<TextView?>(R.id.txtStatus)
        
        // Verificar status de conectividade em tempo real
        CoroutineScope(Dispatchers.IO).launch {
            val wifiConnected = wifiConnectivityManager.isWiFiConnected()
            val wifiWithoutInternet = wifiConnectivityManager.isWiFiConnectedWithoutInternet()
            val networkName = wifiConnectivityManager.getCurrentNetworkName()
            val queueStats = mqttHandler.getQueueStats()
            val queueSize = queueStats["totalMessages"] as? Int ?: 0
            
            runOnUiThread {
                when {
                    wifiWithoutInternet -> {
                        val queueText = if (queueSize > 0) " (Fila: $queueSize)" else ""
                        txtStatus?.text = "WiFi: ${networkName ?: "Conectado"} (Sem Internet)$queueText"
                    }
                    !wifiConnected -> {
                        val queueText = if (queueSize > 0) " (Fila: $queueSize)" else ""
                        txtStatus?.text = "Sem WiFi$queueText"
                    }
                    mqttConnected && wifiConnected -> {
                        val queueText = if (queueSize > 0) " (Enviando fila: $queueSize)" else ""
                        txtStatus?.text = "WiFi: ${networkName ?: "Conectado"} - MQTT OK$queueText"
                    }
                    wifiConnected -> {
                        val queueText = if (queueSize > 0) " (Fila: $queueSize)" else ""
                        txtStatus?.text = "WiFi: ${networkName ?: "Conectado"}$queueText"
                    }
                    else -> {
                        txtStatus?.text = "Verificando conexão..."
                    }
                }
            }
        }
    }
    
    private fun setupMqttTimer() {
        // Timer será iniciado quando conectar ao MQTT
    }
    
    private fun startMqttSendTimer() {
        stopMqttSendTimer() // Parar timer anterior se existir
        
        mqttSendTimer = object : CountDownTimer(nextSendTime, 1000) {
            override fun onTick(millisUntilFinished: Long) {
                val seconds = millisUntilFinished / 1000
                runOnUiThread {
                    val btnConectar = findViewById<Button>(R.id.btnConectar)
                    
                    // Verificar status WiFi antes de mostrar countdown
                    if (isWifiConnected) {
                        btnConectar.text = "Desconectar (${seconds}s)"
                    } else {
                        btnConectar.text = "Sem WiFi (${seconds}s)"
                    }
                    
                    // Atualizar status com informações da fila
                    updateConnectionStatus()
                }
            }
            
            override fun onFinish() {
                runOnUiThread {
                    val btnConectar = findViewById<Button>(R.id.btnConectar)
                    
                    // Verificar conectividade antes de tentar enviar
                    CoroutineScope(Dispatchers.IO).launch {
                        val wifiOk = wifiConnectivityManager.isWiFiConnected()
                        val networkName = wifiConnectivityManager.getCurrentNetworkName()
                        
                        runOnUiThread {
                            if (wifiOk) {
                                btnConectar.text = "Enviando..."
                                val txtStatus = findViewById<TextView?>(R.id.txtStatus)
                                txtStatus?.text = "Enviando via WiFi: ${networkName ?: "Conectado"}"
                            } else {
                                btnConectar.text = "Sem WiFi!"
                                val txtStatus = findViewById<TextView?>(R.id.txtStatus)
                                txtStatus?.text = "Sem WiFi - Envio cancelado"
                            }
                            
                            // Voltar ao status normal após alguns segundos e reiniciar timer
                            android.os.Handler(android.os.Looper.getMainLooper()).postDelayed({
                                if (mqttConnected) {
                                    updateConnectionStatus()
                                    startMqttSendTimer() // Reiniciar timer
                                }
                            }, AppConfig.UI_SENDING_FEEDBACK_DELAY_MS) // Tempo para mostrar feedback "Enviando..."
                        }
                    }
                }
            }
        }.start()
    }
    
    private fun stopMqttSendTimer() {
        mqttSendTimer?.cancel()
        mqttSendTimer = null
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
        
        // Limpar monitoramento de rede
        networkCallback?.let { callback ->
            connectivityManager.unregisterNetworkCallback(callback)
        }
        
        // Parar timer MQTT
        stopMqttSendTimer()
        
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