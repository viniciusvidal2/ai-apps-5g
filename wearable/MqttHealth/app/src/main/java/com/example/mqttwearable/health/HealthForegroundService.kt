package com.sae5g.mqttwearable.health

import android.app.Service
import android.content.Context
import android.content.Intent
import android.bluetooth.BluetoothAdapter
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import com.sae5g.mqttwearable.R
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import com.sae5g.mqttwearable.mqtt.MqttHandler
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Handler
import android.os.Looper
import com.sae5g.mqttwearable.data.DeviceIdManager
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import android.util.Log
import com.sae5g.mqttwearable.sensors.FallDetector
import com.sae5g.mqttwearable.location.LocationManager
import android.os.Vibrator
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.IntentFilter
import androidx.core.app.NotificationManagerCompat
import com.sae5g.mqttwearable.presentation.EmergencyAlertActivity
import com.sae5g.mqttwearable.connectivity.WiFiConnectivityManager
import com.sae5g.mqttwearable.config.AppConfig
import com.sae5g.mqttwearable.config.FallenConfig
import com.sae5g.mqttwearable.config.BluetoothConfig
import java.util.Calendar

class HealthForegroundService : Service(), SensorEventListener {
    private lateinit var wakeLock: PowerManager.WakeLock
    private var mqttHandler: MqttHandler? = null
    private var healthPublisher: HealthPublisher? = null
    private var isCollecting = false

    // Sensores e acelerômetro
    private lateinit var sensorManager: SensorManager
    private var accelerometer: Sensor? = null
    private var accelerometerX: Float = 0f
    private var accelerometerY: Float = 0f
    private var accelerometerZ: Float = 0f
    private lateinit var accelerometerPublishHandler: Handler
    private var accelerometerPublishRunnable: Runnable? = null
    private var accelerometerPublishingActive = false

    // Detecção de queda e componentes relacionados
    private lateinit var fallDetector: FallDetector
    private lateinit var vibrator: Vibrator
    private lateinit var locationManager: LocationManager
    private var currentLatitude: Double? = null
    private var currentLongitude: Double? = null
    private var fallAlertHandler: Handler? = null
    private var fallAlertCountdown = 10
    private var isFallAlertActive = false
    private lateinit var notificationManager: NotificationManager
    private var fallDetectionActive = false
    private lateinit var wifiConnectivityManager: WiFiConnectivityManager

    // Verificação periódica de Bluetooth
    private lateinit var bluetoothCheckHandler: Handler
    private var bluetoothCheckRunnable: Runnable? = null

    // IDs para notificações
    private val FALL_ALERT_NOTIFICATION_ID = 2
    private val ACTION_CANCEL_FALL_ALERT = "CANCEL_FALL_ALERT"
    private val FALL_ALERT_CHANNEL_ID = "fall_alert_channel"
    private val BLUETOOTH_ALERT_CHANNEL_ID = "bluetooth_alert_channel"
    private val BLUETOOTH_ALERT_NOTIFICATION_ID = 3

    // Receptor para cancelar alerta de queda
    private val fallAlertCancelReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action == ACTION_CANCEL_FALL_ALERT) {
                cancelFallAlert()
            }
        }
    }

    override fun onCreate() {
        super.onCreate()
        // 1. Adquire o WakeLock (permite CPU ativo mesmo com tela apagada)
        val pm = getSystemService(Context.POWER_SERVICE) as PowerManager
        wakeLock = pm.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "MqttHealth:WakeLockTag"
        )
        wakeLock.acquire()

        // 2. Cria a notificação de foreground
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("HealthPublisher ativo")
            .setContentText("Coletando dados em segundo plano…")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .build()

        startForeground(ONGOING_NOTIFICATION_ID, notification)

        // Inicializar gerenciador de conectividade WiFi
        wifiConnectivityManager = WiFiConnectivityManager(applicationContext)
        
        // Inicializar sensores e detecção de queda
        setupAccelerometer()
        setupFallDetection()

        // Criar canal de notificação específico para alertas de queda (IMPORTANCE_HIGH)
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
            val fallChannel = android.app.NotificationChannel(
                FALL_ALERT_CHANNEL_ID,
                "Alertas de Queda",
                android.app.NotificationManager.IMPORTANCE_HIGH
            )
            fallChannel.description = "Notificações de queda com ação de cancelamento"
            notificationManager.createNotificationChannel(fallChannel)

            val bluetoothChannel = android.app.NotificationChannel(
                BLUETOOTH_ALERT_CHANNEL_ID,
                "Alertas de Bluetooth",
                android.app.NotificationManager.IMPORTANCE_HIGH
            )
            bluetoothChannel.description = "Avisos quando Bluetooth está ligado no horário comercial"
            notificationManager.createNotificationChannel(bluetoothChannel)
        }

        // Registrar receiver para cancelar alerta (API 33+: precisa especificar flag de exportação)
        val filter = IntentFilter(ACTION_CANCEL_FALL_ALERT)
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(
                fallAlertCancelReceiver,
                filter,
                Context.RECEIVER_NOT_EXPORTED
            )
        } else {
            registerReceiver(fallAlertCancelReceiver, filter)
        }

        // Iniciar monitoramento periódico do Bluetooth
        startBluetoothMonitoring()
    }

    private fun setupAccelerometer() {
        // Inicializar o DeviceIdManager
        DeviceIdManager.initializeDeviceId(this)
        
        // Configurar SensorManager
        sensorManager = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        accelerometer = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
        
        // Inicializar handler para publicação
        accelerometerPublishHandler = Handler(Looper.getMainLooper())
        
        Log.d("HealthForegroundService", "Accelerometer setup completed")
    }

    private fun setupFallDetection() {
        // Inicializar componentes
        vibrator = getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
        locationManager = LocationManager(applicationContext)
        notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        
        // Configurar handler para alertas de queda
        fallAlertHandler = Handler(Looper.getMainLooper())
        
        // Configurar listener de localização
        locationManager.setLocationUpdateListener(object : LocationManager.LocationUpdateListener {
            override fun onLocationUpdate(latitude: Double, longitude: Double) {
                currentLatitude = latitude
                currentLongitude = longitude
                Log.d("HealthForegroundService", "GPS: $latitude, $longitude")
            }
            
            override fun onLocationError(error: String) {
                Log.e("HealthForegroundService", "GPS Erro: $error")
            }
        })
        
        // Iniciar atualizações de localização
        locationManager.startLocationUpdates()
        
        // Configurar detector de queda
        fallDetector = FallDetector()
        fallDetector.setFallDetectionListener(object : FallDetector.FallDetectionListener {
            override fun onFallDetected() {
                Log.d("HealthForegroundService", "Fall detected in background!")
                startFallAlert()
            }
            
            override fun onStateChanged(state: String, magnitude: Float) {
                Log.d("HealthForegroundService", "FallDetector: $state - Magnitude: $magnitude")
            }
        })
        
        Log.d("HealthForegroundService", "Fall detection setup completed")
    }

    private fun startAccelerometerCollection() {
        if (accelerometer != null && !fallDetectionActive) {
            sensorManager.registerListener(this, accelerometer, SensorManager.SENSOR_DELAY_UI)
            fallDetectionActive = true
            Log.d("HealthForegroundService", "Accelerometer collection and fall detection started")
            
            // Publicação MQTT do acelerômetro desativada a pedido do usuário
            // startAccelerometerPublishing()
        }
    }

    private fun stopAccelerometerCollection() {
        if (fallDetectionActive) {
            sensorManager.unregisterListener(this)
            fallDetectionActive = false
            // stopAccelerometerPublishing() // desativado
            Log.d("HealthForegroundService", "Accelerometer collection and fall detection stopped")
        }
    }

    private fun startAccelerometerPublishing() {
        if (accelerometerPublishingActive) return
        
        accelerometerPublishingActive = true
        
        accelerometerPublishRunnable = object : Runnable {
            override fun run() {
                if (accelerometerPublishingActive && mqttHandler != null) {
                    publishAccelerometerData()
                    accelerometerPublishHandler.postDelayed(this, 1000) // 1 segundo
                }
            }
        }
        
        accelerometerPublishHandler.post(accelerometerPublishRunnable!!)
        Log.d("HealthForegroundService", "Accelerometer publishing started")
    }
    
    private fun stopAccelerometerPublishing() {
        accelerometerPublishingActive = false
        accelerometerPublishRunnable?.let {
            accelerometerPublishHandler.removeCallbacks(it)
        }
        Log.d("HealthForegroundService", "Accelerometer publishing stopped")
    }
    
    private fun publishAccelerometerData() {
        // Criar JSON com horário atual em formato ISO 8601 UTC
        val sdf = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
        sdf.timeZone = TimeZone.getTimeZone("UTC")
        val currentTime = sdf.format(Date())
        
        // Criar JSON com dados do acelerômetro
        val accelerometerMessage = buildString {
            append("{")
            append("\"time\":\"$currentTime\",")
            append("\"id\":\"${DeviceIdManager.getDeviceId()}\",")
            append("\"accelerometer\":{")
            append("\"x\":${String.format("%.2f", accelerometerX)},")
            append("\"y\":${String.format("%.2f", accelerometerY)},")
            append("\"z\":${String.format("%.2f", accelerometerZ)}")
            append("}")
            append("}")
        }
        
        // Publicar no tópico /accelerometer
        mqttHandler?.publish("/accelerometer", accelerometerMessage) { success ->
            if (success) {
                Log.d("HealthForegroundService", "Accelerometer data published")
            } else {
                Log.e("HealthForegroundService", "Failed to publish accelerometer data")
            }
        }
    }

    // MÉTODOS DE DETECÇÃO DE QUEDA EM SEGUNDO PLANO

    private fun startFallAlert() {
        if (isFallAlertActive) return
        
        isFallAlertActive = true
        fallAlertCountdown = FallenConfig.FALL_ALERT_COUNTDOWN_SECONDS
        
        Log.d("HealthForegroundService", "Starting fall alert in background")
        
        // Tentar abrir EmergencyAlertActivity primeiro
        tryOpenEmergencyActivity()
        
        // Criar notificação de backup
        showFallAlertNotification()
        
        // Iniciar vibração e countdown
        startFallAlertCountdown()
    }

    private fun tryOpenEmergencyActivity() {
        try {
            val intent = Intent(this, EmergencyAlertActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            intent.putExtra("CURRENT_LATITUDE", currentLatitude)
            intent.putExtra("CURRENT_LONGITUDE", currentLongitude)
            startActivity(intent)
            Log.d("HealthForegroundService", "EmergencyAlertActivity opened successfully")
        } catch (e: Exception) {
            Log.e("HealthForegroundService", "Failed to open EmergencyAlertActivity: ${e.message}")
            // A notificação já foi criada como backup
        }
    }

    private fun showFallAlertNotification() {
        val cancelIntent = Intent(this, HealthForegroundService::class.java).apply {
            action = ACTION_CANCEL_FALL_ALERT
        }
        val cancelPendingIntent = PendingIntent.getService(
            this, 0, cancelIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        // PendingIntent para abrir a tela de emergência caso usuário toque na notificação
        val fullScreenIntent = Intent(this, EmergencyAlertActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("CURRENT_LATITUDE", currentLatitude)
            putExtra("CURRENT_LONGITUDE", currentLongitude)
        }
        val fullScreenPendingIntent = PendingIntent.getActivity(
            this, 1, fullScreenIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(this, FALL_ALERT_CHANNEL_ID)
            .setContentTitle("Queda")
            .setContentText("Enviando alerta em $fallAlertCountdown segundos...")
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setAutoCancel(false)
            .setOngoing(true)
            .setFullScreenIntent(fullScreenPendingIntent, true)
            .addAction(
                android.R.drawable.ic_delete,
                "CANCELAR",
                cancelPendingIntent
            )
            .build()

        notificationManager.notify(FALL_ALERT_NOTIFICATION_ID, notification)
    }

    private fun updateFallAlertNotification() {
        val cancelIntent = Intent(this, HealthForegroundService::class.java).apply {
            action = ACTION_CANCEL_FALL_ALERT
        }
        val cancelPendingIntent = PendingIntent.getService(
            this, 0, cancelIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val notification = NotificationCompat.Builder(this, FALL_ALERT_CHANNEL_ID)
            .setContentTitle("Queda")
            .setContentText("Enviando alerta em $fallAlertCountdown segundos...")
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setAutoCancel(false)
            .setOngoing(true)
            .addAction(
                android.R.drawable.ic_delete,
                "CANCELAR",
                cancelPendingIntent
            )
            .build()
        notificationManager.notify(FALL_ALERT_NOTIFICATION_ID, notification)
    }

    private fun startFallAlertCountdown() {
        val vibrationRunnable = object : Runnable {
            override fun run() {
                if (isFallAlertActive && fallAlertCountdown > 0) {
                    // Vibrar
                    if (vibrator.hasVibrator()) {
                        vibrator.vibrate(FallenConfig.FALL_ALERT_VIBRATION_DURATION_MS)
                    }
                    
                    // Atualizar notificação
                    updateFallAlertNotification()
                    fallAlertCountdown--
                    
                    // Agendar próxima vibração
                    fallAlertHandler?.postDelayed(this, FallenConfig.FALL_ALERT_VIBRATION_INTERVAL_MS)
                } else if (isFallAlertActive && fallAlertCountdown <= 0) {
                    // Tempo esgotado - enviar alerta
                    sendFallAlert()
                }
            }
        }
        
        fallAlertHandler?.post(vibrationRunnable)
    }

    private fun sendFallAlert() {
        Log.d("HealthForegroundService", "Iniciando processo de envio de alerta de queda...")
        
        // Primeiro verificar conectividade WiFi
        CoroutineScope(Dispatchers.IO).launch {
            // Extrair IP do servidor MQTT
            val mqttServerIp = extractMqttServerIp()
            
            if (mqttServerIp == null) {
                Log.e("HealthForegroundService", "Não foi possível determinar IP do servidor MQTT")
                showConnectivityNotification("❌ Erro de Configuração", "IP do servidor MQTT não encontrado")
                cleanupFallAlert()
                return@launch
            }
            
            wifiConnectivityManager.checkFullConnectivity(mqttServerIp) { result ->
                when (result) {
                    WiFiConnectivityManager.ConnectivityResult.FULL_CONNECTIVITY -> {
                        Log.d("HealthForegroundService", "Conectividade completa verificada, enviando alerta...")
                        performFallAlertSend()
                    }
                    WiFiConnectivityManager.ConnectivityResult.WIFI_ONLY -> {
                        Log.w("HealthForegroundService", "WiFi conectado mas servidor MQTT inacessível")
                        showConnectivityNotification("❌ Sem WiFi", "Servidor MQTT inacessível - Alerta não enviado")
                        cleanupFallAlert()
                    }
                    WiFiConnectivityManager.ConnectivityResult.NO_WIFI -> {
                        Log.w("HealthForegroundService", "Sem conexão WiFi")
                        showConnectivityNotification("❌ Sem WiFi", "Conecte-se a uma rede WiFi para enviar alertas")
                        cleanupFallAlert()
                    }
                }
            }
        }
    }
    
    private fun extractMqttServerIp(): String? {
        return try {
            val cachedBrokerUrl = mqttHandler?.getCachedBrokerUrl() ?: return null
            // Formato: tcp://IP:1883
            cachedBrokerUrl.replace("tcp://", "").split(":")[0]
        } catch (e: Exception) {
            Log.e("HealthForegroundService", "Erro ao extrair IP do broker URL", e)
            null
        }
    }
    
    private fun showConnectivityNotification(title: String, message: String) {
        val notification = NotificationCompat.Builder(this, FALL_ALERT_CHANNEL_ID)
            .setContentTitle(title)
            .setContentText(message)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .build()

        notificationManager.notify(FALL_ALERT_NOTIFICATION_ID + 1, notification)
    }
    
    private fun performFallAlertSend() {
        // Criar JSON com horário atual em formato ISO 8601 UTC
        val sdf = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
        sdf.timeZone = TimeZone.getTimeZone("UTC")
        val currentTime = sdf.format(Date())
        
        // Criar JSON com Device ID, localização e dados de queda
        val fallMessage = buildString {
            append("{")
            append("\"time\":\"$currentTime\",")
            append("\"fall\":1,")
            append("\"emergency\":1,")
            append("\"id\":\"${DeviceIdManager.getDeviceId()}\"")
            
            // Adicionar localização se disponível
            if (currentLatitude != null && currentLongitude != null) {
                append(",\"latitude\":$currentLatitude,\"longitude\":$currentLongitude")
            }
            
            append("}")
        }
        
        // Enviar mensagem MQTT para o tópico /fall
        mqttHandler?.publish("/fall", fallMessage) { success ->
            val resultNotification = NotificationCompat.Builder(this, FALL_ALERT_CHANNEL_ID)
                .setContentTitle(if (success) "✅ Alerta Enviado!" else "❌ Erro no Envio!")
                .setContentText(if (success) "Alerta de emergência foi enviado com sucesso" else "Falha ao enviar alerta de emergência")
                .setSmallIcon(if (success) android.R.drawable.ic_dialog_info else android.R.drawable.ic_dialog_alert)
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setAutoCancel(true)
                .build()

            notificationManager.notify(FALL_ALERT_NOTIFICATION_ID + 1, resultNotification)
            
            Log.d("HealthForegroundService", "Fall alert sent: $success - $fallMessage")
        }
        
        // Limpar alerta
        cleanupFallAlert()
    }

    private fun cancelFallAlert() {
        Log.d("HealthForegroundService", "Fall alert cancelled by user")
        
        val cancelledNotification = NotificationCompat.Builder(this, FALL_ALERT_CHANNEL_ID)
            .setContentTitle("✅ Alerta Cancelado")
            .setContentText("Alerta de queda foi cancelado pelo usuário")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setAutoCancel(true)
            .build()

        notificationManager.notify(FALL_ALERT_NOTIFICATION_ID + 2, cancelledNotification)
        
        cleanupFallAlert()
    }

    private fun cleanupFallAlert() {
        isFallAlertActive = false
        fallAlertHandler?.removeCallbacksAndMessages(null)
        
        // Parar vibração
        vibrator.cancel()
        
        // Remover notificação de alerta
        notificationManager.cancel(FALL_ALERT_NOTIFICATION_ID)
    }

    // MONITORAMENTO PERIÓDICO DO BLUETOOTH
    private fun startBluetoothMonitoring() {
        bluetoothCheckHandler = Handler(Looper.getMainLooper())
        bluetoothCheckRunnable = object : Runnable {
            override fun run() {
                try {
                    val now = Calendar.getInstance()
                    val withinWindow = BluetoothConfig.isWithinActiveWindow(now)
                    val isBluetoothEnabled = BluetoothAdapter.getDefaultAdapter()?.isEnabled == true

                    if (withinWindow && isBluetoothEnabled) {
                        // Vibrar conforme configuração
                        if (vibrator.hasVibrator()) {
                            vibrator.vibrate(BluetoothConfig.VIBRATION_DURATION_MS)
                        }
                        // Notificar usuário
                        val notification = NotificationCompat.Builder(this@HealthForegroundService, BLUETOOTH_ALERT_CHANNEL_ID)
                            .setContentTitle(BluetoothConfig.NOTIFICATION_TITLE)
                            .setContentText(BluetoothConfig.NOTIFICATION_TEXT)
                            .setSmallIcon(android.R.drawable.ic_dialog_alert)
                            .setPriority(NotificationCompat.PRIORITY_HIGH)
                            .setCategory(NotificationCompat.CATEGORY_ALARM)
                            .setAutoCancel(true)
                            .build()
                        notificationManager.notify(BLUETOOTH_ALERT_NOTIFICATION_ID, notification)
                    }
                } catch (e: Exception) {
                    Log.e("HealthForegroundService", "Erro no monitoramento de Bluetooth", e)
                } finally {
                    // Reagendar próxima verificação
                    bluetoothCheckHandler.postDelayed(this, BluetoothConfig.CHECK_INTERVAL_MS)
                }
            }
        }
        // Primeira execução imediata
        bluetoothCheckHandler.post(bluetoothCheckRunnable!!)
    }

    private fun stopBluetoothMonitoring() {
        bluetoothCheckRunnable?.let { bluetoothCheckHandler.removeCallbacks(it) }
    }

    override fun onSensorChanged(event: SensorEvent?) {
        event?.let { sensorEvent ->
            if (sensorEvent.sensor.type == Sensor.TYPE_ACCELEROMETER) {
                accelerometerX = sensorEvent.values[0]
                accelerometerY = sensorEvent.values[1]
                accelerometerZ = sensorEvent.values[2]
                
                // Processar dados para detecção de queda (apenas se não estiver em alerta)
                if (!isFallAlertActive) {
                    fallDetector.processSensorData(accelerometerX, accelerometerY, accelerometerZ)
                }
            }
        }
    }
    
    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {
        // Não é necessário implementar para este caso de uso
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if(intent?.action == ACTION_CANCEL_FALL_ALERT){
            cancelFallAlert()
            return START_STICKY
        }
        // Recebe o IP do broker via Intent
        val brokerIp = intent?.getStringExtra(EXTRA_BROKER_IP)
        if (!isCollecting && brokerIp != null) {
            isCollecting = true
            val brokerUrl = "tcp://$brokerIp:1883"
            mqttHandler = MqttHandler(this)
            healthPublisher = HealthPublisher(this, mqttHandler!!)
            CoroutineScope(Dispatchers.IO).launch {
                mqttHandler?.connect(brokerUrl, "wearable-background-${System.currentTimeMillis()}") { connected ->
                    if (connected) {
                        CoroutineScope(Dispatchers.IO).launch {
                            healthPublisher?.startPassiveMeasure()
                        }
                        // Iniciar coleta do acelerômetro e detecção de queda quando conectado
                        startAccelerometerCollection()
                    }
                }
            }
        }
        return START_STICKY
    }

    override fun onDestroy() {
        super.onDestroy()
        wakeLock.release()
        healthPublisher?.stopPassiveMeasure()
        stopAccelerometerCollection()
        locationManager.stopLocationUpdates()
        accelerometerPublishHandler.removeCallbacksAndMessages(null)
        stopBluetoothMonitoring()
        
        // Limpar alertas de queda
        if (isFallAlertActive) {
            cleanupFallAlert()
        }
        fallAlertHandler?.removeCallbacksAndMessages(null)
        
        // Desregistrar receiver
        unregisterReceiver(fallAlertCancelReceiver)
        
        mqttHandler?.disconnect()
        isCollecting = false
    }

    override fun onBind(intent: Intent?) = null

    companion object {
        const val CHANNEL_ID = "health_foreground_channel"
        const val ONGOING_NOTIFICATION_ID = 1
        const val EXTRA_BROKER_IP = "extra_broker_ip"
    }
}