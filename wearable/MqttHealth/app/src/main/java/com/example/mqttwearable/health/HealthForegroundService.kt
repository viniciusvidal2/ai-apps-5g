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

class HealthForegroundService : Service() {
    private lateinit var wakeLock: PowerManager.WakeLock
    private var mqttHandler: MqttHandler? = null
    private var healthPublisher: HealthPublisher? = null
    private var isCollecting = false

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
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // Recebe o IP do broker via Intent
        val brokerIp = intent?.getStringExtra(EXTRA_BROKER_IP)
        if (!isCollecting && brokerIp != null) {
            isCollecting = true
            val brokerUrl = "tcp://$brokerIp:1883"
            mqttHandler = MqttHandler(this)
            healthPublisher = HealthPublisher(this, mqttHandler!!)
            CoroutineScope(Dispatchers.IO).launch {
                mqttHandler?.connect(brokerUrl, "wearable-${System.currentTimeMillis()}") { connected ->
                    if (connected) {
                        CoroutineScope(Dispatchers.IO).launch {
                            healthPublisher?.startPassiveMeasure()
                        }
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