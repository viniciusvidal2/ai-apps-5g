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
    private lateinit var stepCounterService: StepCounterService
    
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
        override fun onAvailabilityChanged(dataType: DeltaDataType<*, *>, availability: Availability) {
            Log.d(TAG, "Disponibilidade do sensor de frequência cardíaca alterada: $availability")
        }

        override fun onDataReceived(data: DataPointContainer) {
            exerciseMetrics = exerciseMetrics.update(data)
            updateNotification()
        }
    }
    
    private val stepsCallback = object : MeasureCallback {
        override fun onAvailabilityChanged(dataType: DeltaDataType<*, *>, availability: Availability) {
            Log.d(TAG, "Disponibilidade do sensor de passos alterada: $availability")
        }

        override fun onDataReceived(data: DataPointContainer) {
            exerciseMetrics = exerciseMetrics.update(data)
            updateNotification()
        }
    }

    private val distanceCallback = object : MeasureCallback {
        override fun onAvailabilityChanged(dataType: DeltaDataType<*, *>, availability: Availability) {
            Log.d(TAG, "Disponibilidade do sensor de distância alterada: $availability")
        }

        override fun onDataReceived(data: DataPointContainer) {
            exerciseMetrics = exerciseMetrics.update(data)
            updateNotification()
        }
    }

    private val caloriesCallback = object : MeasureCallback {
        override fun onAvailabilityChanged(dataType: DeltaDataType<*, *>, availability: Availability) {
            Log.d(TAG, "Disponibilidade do sensor de calorias alterada: $availability")
        }

        override fun onDataReceived(data: DataPointContainer) {
            exerciseMetrics = exerciseMetrics.update(data)
            updateNotification()
        }
    }

    private val speedCallback = object : MeasureCallback {
        override fun onAvailabilityChanged(dataType: DeltaDataType<*, *>, availability: Availability) {
            Log.d(TAG, "Disponibilidade do sensor de velocidade alterada: $availability")
        }

        override fun onDataReceived(data: DataPointContainer) {
            exerciseMetrics = exerciseMetrics.update(data)
            updateNotification()
        }
    }

    private val elevationCallback = object : MeasureCallback {
        override fun onAvailabilityChanged(dataType: DeltaDataType<*, *>, availability: Availability) {
            Log.d(TAG, "Disponibilidade do sensor de elevação alterada: $availability")
        }

        override fun onDataReceived(data: DataPointContainer) {
            exerciseMetrics = exerciseMetrics.update(data)
            updateNotification()
        }
    }

    private val paceCallback = object : MeasureCallback {
        override fun onAvailabilityChanged(dataType: DeltaDataType<*, *>, availability: Availability) {
            Log.d(TAG, "Disponibilidade do sensor de ritmo alterada: $availability")
        }

        override fun onDataReceived(data: DataPointContainer) {
            exerciseMetrics = exerciseMetrics.update(data)
            updateNotification()
        }
    }
    
    override fun onCreate() {
        super.onCreate()
        Log.d(TAG, "Serviço criado")
        
        mainApplication = application as MainApplication
        
        // Inicializa o serviço de contagem de passos
        stepCounterService = StepCounterService(this)
        
        // Inicia a subscrição para contagem de passos com a Recording API
        serviceScope.launch {
            if (stepCounterService.isGooglePlayServicesAvailable()) {
                val success = stepCounterService.subscribeToStepCount()
                if (success) {
                    Log.d(TAG, "Subscrição para contagem de passos iniciada com sucesso")
                    
                    // Agenda atualizações periódicas da contagem de passos
                    startStepCountUpdates()
                } else {
                    Log.e(TAG, "Falha ao iniciar subscrição para contagem de passos")
                }
            } else {
                Log.w(TAG, "Google Play Services não disponível na versão necessária")
            }
        }
        
        // Registra o receptor de bateria
        registerReceiver(batteryReceiver, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
        
        // Cria o canal de notificação (para Android 8.0+)
        createNotificationChannel()
        
        // Inicializa o MeasureClient para monitoramento de métricas de saúde
        measureClient = HealthServices.getClient(this).measureClient
        
        // Registra todos os callbacks de métricas
        serviceScope.launch {
            try {
                // Registrar callbacks de medição (exceto passos, que usará Recording API)
                measureClient.registerMeasureCallback(DataType.HEART_RATE_BPM, heartRateCallback)
                // Mantemos o callback da Health Services API como fallback
                measureClient.registerMeasureCallback(DataType.STEPS, stepsCallback)
                measureClient.registerMeasureCallback(DataType.DISTANCE, distanceCallback)
                measureClient.registerMeasureCallback(DataType.CALORIES, caloriesCallback)
                measureClient.registerMeasureCallback(DataType.SPEED, speedCallback)
                measureClient.registerMeasureCallback(DataType.ELEVATION_GAIN, elevationCallback)
                measureClient.registerMeasureCallback(DataType.PACE, paceCallback)
                
                Log.d(TAG, "Todos os callbacks de medição registrados com sucesso")
            } catch (e: Exception) {
                Log.e(TAG, "Erro ao registrar callbacks de medição", e)
                e.printStackTrace()
            }
        }
        
        // Inicia a publicação MQTT se houver conexão
        startPublishingData()
    }
    
    private fun startStepCountUpdates() {
        serviceScope.launch {
            while (true) {
                try {
                    val steps = stepCounterService.readStepCountData()
                    if (steps > 0) {
                        // Atualiza passos e calcula distância e calorias com base neles
                        exerciseMetrics = exerciseMetrics.updateSteps(steps)
                            .calculateDistanceFromSteps()
                            .calculateCaloriesFromSteps()
                        
                        updateNotification()
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Erro ao ler contagem de passos", e)
                }
                delay(60000) // Atualiza a cada minuto
            }
        }
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
        
        // Cria a notificação com mais informações
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Monitorando Saúde")
            .setContentText("""
                FC: ${exerciseMetrics.heartRate ?: "--"} BPM
                Passos: ${exerciseMetrics.steps ?: "--"}
                Distância: ${String.format("%.1f", exerciseMetrics.distance ?: 0.0)}m
                Bateria: ${exerciseMetrics.batteryLevel ?: "--"}%
            """.trimIndent())
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentIntent(pendingIntent)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setStyle(NotificationCompat.BigTextStyle())
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
        
        // Cancelar o monitoramento de métricas
        serviceScope.launch {
            try {
                // A API atual não suporta unregisterMeasureCallback
                // Uma alternativa é cancelar as coroutines, o que faremos abaixo
                Log.d(TAG, "Encerrando monitoramento de métricas")
                
                // Cancelar subscrição para contagem de passos
                stepCounterService.unsubscribeFromStepCount()
            } catch (e: Exception) {
                Log.e(TAG, "Erro ao cancelar monitoramento", e)
                e.printStackTrace()
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
        
        // Cancelar todas as coroutines (isso efetivamente interrompe o processamento dos callbacks)
        serviceScope.cancel()
    }
} 