package com.projetosae5g.app_5g_layout

import android.app.*
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.health.services.client.HealthServices
import androidx.health.services.client.MeasureCallback
import androidx.health.services.client.MeasureClient
import androidx.health.services.client.data.Availability
import androidx.health.services.client.data.DataPointContainer
import androidx.health.services.client.data.DataType
import androidx.health.services.client.data.DeltaDataType
import kotlinx.coroutines.*

class MonitorService : Service() {
    private val TAG = "MonitorService"
    private val NOTIFICATION_ID = 1001
    private val CHANNEL_ID = "MonitorServiceChannel"
    
    private lateinit var measureClient: MeasureClient
    private var exerciseMetrics = ExerciseMetrics()
    private var measurementInterval: Long = 60 // segundos (padrão para envio)
    private val serviceScope = CoroutineScope(Dispatchers.Default)
    
    private lateinit var mainApplication: MainApplication
    
    // BroadcastReceiver para monitorar o nível da bateria
    private val batteryReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            if (intent.action == Intent.ACTION_BATTERY_CHANGED) {
                val level = intent.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
                val scale = intent.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
                val batteryPct = level * 100 / scale
                exerciseMetrics = exerciseMetrics.copy(batteryLevel = batteryPct)
                updateNotification()
            }
        }
    }
    
    // Callback de medição de frequência cardíaca
    private val heartRateCallback = object : MeasureCallback {
        override fun onDataReceived(data: DataPointContainer) {
            // Atualiza os dados de batimentos cardíacos
            exerciseMetrics = exerciseMetrics.update(data)
            updateNotification()
        }

        override fun onAvailabilityChanged(
            dataType: DeltaDataType<*, *>,
            availability: Availability
        ) {
            Log.d(TAG, "onAvailabilityChanged: dataType=$dataType, availability=$availability")
        }
    }
    
    override fun onCreate() {
        super.onCreate()
        Log.d(TAG, "Serviço criado")
        
        mainApplication = application as MainApplication
        
        // Registra o receptor de bateria
        registerReceiver(batteryReceiver, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
        
        // Cria o canal de notificação (para Android 8.0+)
        createNotificationChannel()
        
        // Inicializa o MeasureClient para monitoramento de frequência cardíaca
        measureClient = HealthServices.getClient(this).measureClient
        
        // Inicializa o MeasureClient de forma simplificada
        serviceScope.launch {
            try {
                measureClient.registerMeasureCallback(DataType.HEART_RATE_BPM, heartRateCallback)
            } catch (e: Exception) {
                Log.e(TAG, "Erro ao registrar callback de batimentos cardíacos", e)
            }
        }
        
        // Inicia a publicação MQTT se houver conexão
        startPublishingData()
    }
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.d(TAG, "Serviço iniciado")
        
        // Obtém o intervalo de medição, se fornecido
        intent?.getLongExtra("interval", 60)?.let {
            measurementInterval = it
            Log.d(TAG, "Intervalo de medição definido para $measurementInterval segundos")
        }
        
        // Cria a notificação inicial
        val notification = createNotification()
        startForeground(NOTIFICATION_ID, notification)
        
        return START_STICKY
    }
    
    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val name = "Monitoramento de Saúde"
            val descriptionText = "Canal para o serviço de monitoramento de saúde"
            val importance = NotificationManager.IMPORTANCE_LOW
            val channel = NotificationChannel(CHANNEL_ID, name, importance).apply {
                description = descriptionText
            }
            
            val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }
    
    private fun createNotification(): Notification {
        // Intent para abrir a MainActivity quando a notificação for clicada
        val pendingIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )
        
        // Cria a notificação
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Monitorando Saúde")
            .setContentText("FC: ${exerciseMetrics.heartRate ?: "--"} BPM | Bateria: ${exerciseMetrics.batteryLevel ?: "--"}%")
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentIntent(pendingIntent)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }
    
    private fun updateNotification() {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        notificationManager.notify(NOTIFICATION_ID, createNotification())
    }
    
    private fun startPublishingData() {
        // Fornecer funções que retornam os dados mais recentes
        mainApplication.startMqttPublishing(
            heartRateProvider = { exerciseMetrics.heartRate },
            batteryLevelProvider = { exerciseMetrics.batteryLevel },
            locationProvider = { Pair(exerciseMetrics.latitude, exerciseMetrics.longitude) },
            secondsMeasureProvider = { measurementInterval }
        )
    }
    
    override fun onBind(intent: Intent?): IBinder? {
        return null
    }
    
    override fun onDestroy() {
        super.onDestroy()
        Log.d(TAG, "Serviço destruído")
        
        // Cancelar o monitoramento de batimentos cardíacos
        serviceScope.launch {
            try {
                // Removido a chamada para clearMeasureCallbacks que não existe na versão atual
                Log.d(TAG, "Encerrando callbacks de medição")
            } catch (e: Exception) {
                Log.e(TAG, "Erro ao cancelar monitoramento", e)
            }
        }
        
        // Desregistrar o receptor de bateria
        try {
            unregisterReceiver(batteryReceiver)
        } catch (e: Exception) {
            Log.e(TAG, "Erro ao desregistrar receptor de bateria", e)
        }
        
        // Parar a publicação MQTT
        mainApplication.stopMqttPublishing()
        
        // Cancelar todas as coroutines
        serviceScope.cancel()
    }
} 