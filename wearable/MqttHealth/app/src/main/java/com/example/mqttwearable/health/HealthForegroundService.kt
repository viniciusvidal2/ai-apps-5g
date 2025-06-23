package com.example.mqttwearable.health

import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import com.example.mqttwearable.R
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import com.example.mqttwearable.mqtt.MqttHandler
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Handler
import android.os.Looper
import com.example.mqttwearable.data.DeviceIdManager
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import android.util.Log
import com.example.mqttwearable.sensors.FallDetector
import com.example.mqttwearable.location.LocationManager
import android.os.Vibrator
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.IntentFilter
import androidx.core.app.NotificationManagerCompat
import com.example.mqttwearable.presentation.EmergencyAlertActivity

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

    // IDs para notificações
    private val FALL_ALERT_NOTIFICATION_ID = 2
    private val ACTION_CANCEL_FALL_ALERT = "CANCEL_FALL_ALERT"
    private val FALL_ALERT_CHANNEL_ID = "fall_alert_channel"

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
        fallAlertCountdown = 10
        
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
            .setContentTitle("🚨 QUEDA DETECTADA! 🚨")
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
            .setContentTitle("🚨 QUEDA DETECTADA! 🚨")
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
                        vibrator.vibrate(500) // Vibra por 500ms
                    }
                    
                    // Atualizar notificação
                    updateFallAlertNotification()
                    fallAlertCountdown--
                    
                    // Agendar próxima vibração
                    fallAlertHandler?.postDelayed(this, 1000)
                } else if (isFallAlertActive && fallAlertCountdown <= 0) {
                    // Tempo esgotado - enviar alerta
                    sendFallAlert()
                }
            }
        }
        
        fallAlertHandler?.post(vibrationRunnable)
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