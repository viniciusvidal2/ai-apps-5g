package com.iagoBiundini.mqttwifi.notification

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.provider.Settings
import androidx.core.app.NotificationCompat
import com.iagoBiundini.mqttwifi.R

class NotificationHelper(private val context: Context) {
    
    companion object {
        private const val CHANNEL_ID_SERVICE = "wifi_monitor_service"
        private const val CHANNEL_ID_ALERT = "wifi_alert"
        private const val CHANNEL_NAME_SERVICE = "Monitor WiFi"
        private const val CHANNEL_NAME_ALERT = "Alertas WiFi"
        const val NOTIFICATION_ID_SERVICE = 1
        const val NOTIFICATION_ID_ALERT = 2
    }
    
    private val notificationManager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
    
    init {
        createNotificationChannels()
    }
    
    /**
     * Cria os canais de notificação necessários
     */
    private fun createNotificationChannels() {
        // Canal para o serviço em foreground
        val serviceChannel = NotificationChannel(
            CHANNEL_ID_SERVICE,
            CHANNEL_NAME_SERVICE,
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "Notificação do serviço de monitoramento WiFi"
            setShowBadge(false)
        }
        
        // Canal para alertas de WiFi
        val alertChannel = NotificationChannel(
            CHANNEL_ID_ALERT,
            CHANNEL_NAME_ALERT,
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "Alertas quando WiFi não está conectado"
            enableVibration(true)
            setShowBadge(true)
        }
        
        notificationManager.createNotificationChannel(serviceChannel)
        notificationManager.createNotificationChannel(alertChannel)
    }
    
    /**
     * Cria a notificação persistente para o foreground service
     */
    fun createServiceNotification(): android.app.Notification {
        return NotificationCompat.Builder(context, CHANNEL_ID_SERVICE)
            .setContentTitle("Monitor WiFi Ativo")
            .setContentText("Monitorando conexão WiFi")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setOngoing(true)
            .setSilent(true)
            .build()
    }
    
    /**
     * Mostra notificação de alerta com botões para enviar dados e abrir configurações WiFi
     * e vibra o dispositivo
     */
    fun showWifiAlertNotification() {
        // Vibrar o dispositivo
        vibrateDevice()
        
        // Intent para abrir WiFi settings
        val wifiSettingsIntent = Intent(Settings.ACTION_WIFI_SETTINGS).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        
        // Broadcast para tentar reconectar e enviar (10 tentativas)
        val broadcastWifiIntent = Intent("com.iagoBiundini.mqttwifi.WIFI_BUTTON_CLICKED")
        
        // Broadcast para envio manual imediato
        val broadcastSendNowIntent = Intent("com.iagoBiundini.mqttwifi.SEND_NOW")
        
        val pendingIntentSettings = PendingIntent.getActivity(
            context,
            0,
            wifiSettingsIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        
        val pendingIntentWifiClick = PendingIntent.getBroadcast(
            context,
            1,
            broadcastWifiIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        
        val pendingIntentSendNow = PendingIntent.getBroadcast(
            context,
            2,
            broadcastSendNowIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        
        val notification = NotificationCompat.Builder(context, CHANNEL_ID_ALERT)
            .setContentTitle("WiFi Desconectado")
            .setContentText("Toque para conectar WiFi ou enviar agora")
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(false)
            .addAction(
                android.R.drawable.ic_menu_send,
                "Enviar Agora",
                pendingIntentSendNow
            )
            .addAction(
                android.R.drawable.ic_menu_manage,
                "Conectar WiFi",
                pendingIntentSettings
            )
            .setContentIntent(pendingIntentWifiClick)
            .setVibrate(longArrayOf(0, 500, 200, 500))
            .build()
        
        notificationManager.notify(NOTIFICATION_ID_ALERT, notification)
    }
    
    /**
     * Vibra o dispositivo
     */
    private fun vibrateDevice() {
        val vibrator = context.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
        
        if (vibrator.hasVibrator()) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                // Padrão de vibração: espera 0ms, vibra 500ms, espera 200ms, vibra 500ms
                val pattern = longArrayOf(0, 500, 200, 500)
                val effect = VibrationEffect.createWaveform(pattern, -1)
                vibrator.vibrate(effect)
            } else {
                @Suppress("DEPRECATION")
                vibrator.vibrate(longArrayOf(0, 500, 200, 500), -1)
            }
        }
    }
    
    /**
     * Cancela a notificação de alerta
     */
    fun cancelAlertNotification() {
        notificationManager.cancel(NOTIFICATION_ID_ALERT)
    }
}
