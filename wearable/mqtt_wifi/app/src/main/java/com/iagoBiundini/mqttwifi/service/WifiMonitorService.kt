package com.iagoBiundini.mqttwifi.service

import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.IBinder
import android.util.Log
import com.iagoBiundini.mqttwifi.mqtt.MqttHelper
import com.iagoBiundini.mqttwifi.notification.NotificationHelper
import com.iagoBiundini.mqttwifi.utils.NetworkUtils
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

class WifiMonitorService : Service() {
    
    companion object {
        private const val TAG = "WifiMonitorService"
        const val ACTION_UPDATE_COUNTDOWN = "com.iagoBiundini.mqttwifi.UPDATE_COUNTDOWN"
        const val ACTION_SEND_NOW = "com.iagoBiundini.mqttwifi.SEND_NOW"
        const val ACTION_WIFI_BUTTON_CLICKED = "com.iagoBiundini.mqttwifi.WIFI_BUTTON_CLICKED"
        const val EXTRA_SECONDS_REMAINING = "seconds_remaining"
        
        // Variável configurável para o intervalo de verificação (em segundos)
        const val CHECK_INTERVAL_SECONDS = 60
        
        private const val CHECK_INTERVAL = CHECK_INTERVAL_SECONDS * 1000L
        private const val COUNTDOWN_UPDATE_INTERVAL = 1_000L // 1 segundo
        
        // Configurações para tentativas de envio após clique no botão WiFi
        private const val MQTT_RETRY_DELAY = 5_000L // 5 segundos entre tentativas
        private const val MQTT_MAX_RETRIES = 10 // 10 tentativas
    }
    
    private lateinit var notificationHelper: NotificationHelper
    private lateinit var mqttHelper: MqttHelper
    private val serviceScope = CoroutineScope(Dispatchers.Default + Job())
    private var isLoopRunning = false
    
    private val actionReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            when (intent?.action) {
                ACTION_SEND_NOW -> {
                    Log.d(TAG, "Envio manual solicitado")
                    handleManualSend()
                }
                ACTION_WIFI_BUTTON_CLICKED -> {
                    Log.d(TAG, "Botão WiFi clicado, iniciando tentativas de envio...")
                    handleWifiButtonClick()
                }
            }
        }
    }
    
    override fun onCreate() {
        super.onCreate()
        Log.d(TAG, "Service criado")
        
        notificationHelper = NotificationHelper(this)
        mqttHelper = MqttHelper(this)
        
        // Registrar receiver para ações manuais
        val filter = IntentFilter().apply {
            addAction(ACTION_SEND_NOW)
            addAction(ACTION_WIFI_BUTTON_CLICKED)
        }
        
        // Registrar com ou sem flag dependendo da versão do Android
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(actionReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            registerReceiver(actionReceiver, filter)
        }
        
        // Iniciar como foreground service
        startForeground(
            NotificationHelper.NOTIFICATION_ID_SERVICE,
            notificationHelper.createServiceNotification()
        )
    }
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.d(TAG, "Service iniciado")
        
        // Iniciar o loop de monitoramento apenas se não estiver rodando
        if (!isLoopRunning) {
            isLoopRunning = true
            startMonitoringLoop()
        }
        
        return START_STICKY // Reinicia o serviço se for morto pelo sistema
    }
    
    override fun onBind(intent: Intent?): IBinder? {
        return null
    }
    
    /**
     * Inicia o loop de monitoramento WiFi
     */
    private fun startMonitoringLoop() {
        serviceScope.launch {
            while (isActive) {
                try {
                    // Verifica conectividade WiFi
                    val isWifiConnected = NetworkUtils.isWifiConnected(applicationContext)
                    
                    if (isWifiConnected) {
                        Log.d(TAG, "WiFi conectado - enviando dados MQTT")
                        
                        // Tenta enviar dados via MQTT
                        val success = mqttHelper.publishCurrentTime()
                        if (success) {
                            Log.d(TAG, "Dados enviados com sucesso")
                            // Cancela notificação de alerta se existir
                            notificationHelper.cancelAlertNotification()
                        } else {
                            Log.e(TAG, "Falha ao enviar dados")
                        }
                    } else {
                        Log.d(TAG, "WiFi não conectado - mostrando notificação")
                        
                        // Mostrar notificação e vibrar
                        notificationHelper.showWifiAlertNotification()
                    }
                    
                    // Contagem regressiva
                    for (secondsRemaining in CHECK_INTERVAL_SECONDS downTo 1) {
                        if (!isActive) break
                        
                        // Envia broadcast com o tempo restante
                        sendCountdownBroadcast(secondsRemaining)
                        
                        delay(COUNTDOWN_UPDATE_INTERVAL)
                    }
                    
                } catch (e: Exception) {
                    Log.e(TAG, "Erro no loop de monitoramento: ${e.message}", e)
                    // Em caso de erro, envia broadcast com 60 para não travar a UI
                    sendCountdownBroadcast(60)
                    delay(CHECK_INTERVAL) // Espera antes de tentar novamente
                }
            }
        }
    }
    
    /**
     * Envia broadcast com a contagem regressiva para a UI
     */
    private fun sendCountdownBroadcast(secondsRemaining: Int) {
        val intent = Intent(ACTION_UPDATE_COUNTDOWN).apply {
            putExtra(EXTRA_SECONDS_REMAINING, secondsRemaining)
        }
        sendBroadcast(intent)
    }
    
    override fun onDestroy() {
        super.onDestroy()
        Log.d(TAG, "Service destruído")
        
        // Desregistrar receiver
        try {
            unregisterReceiver(actionReceiver)
        } catch (e: IllegalArgumentException) {
            // Receiver já foi desregistrado
        }
        
        // Cancelar todas as coroutines
        serviceScope.cancel()
        
        // Desconectar MQTT
        mqttHelper.disconnect()
    }
    
    /**
     * Trata envio manual solicitado pelo botão
     */
    private fun handleManualSend() {
        serviceScope.launch {
            try {
                Log.d(TAG, "Processando envio manual...")
                val isWifiConnected = NetworkUtils.isWifiConnected(applicationContext)
                
                if (isWifiConnected) {
                    Log.d(TAG, "WiFi conectado, tentando enviar via MQTT...")
                    val success = mqttHelper.publishCurrentTime()
                    if (success) {
                        Log.d(TAG, "✅ Envio manual bem-sucedido")
                    } else {
                        Log.e(TAG, "❌ Falha no envio manual")
                    }
                } else {
                    Log.w(TAG, "⚠️ WiFi não conectado para envio manual")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Erro no envio manual: ${e.message}", e)
            }
        }
    }
    
    /**
     * Trata clique no botão da notificação WiFi
     * Tenta enviar MQTT 10 vezes com intervalo de 5 segundos em segundo plano
     */
    private fun handleWifiButtonClick() {
        serviceScope.launch {
            try {
                Log.d(TAG, "Processando clique no botão WiFi... Iniciando tentativas de envio MQTT")
                
                var attemptCount = 0
                var success = false
                
                // Tentar enviar até 10 vezes com intervalo de 5 segundos
                while (attemptCount < MQTT_MAX_RETRIES && !success && isActive) {
                    attemptCount++
                    
                    Log.d(TAG, "Tentativa $attemptCount de $MQTT_MAX_RETRIES")
                    
                    // Verificar se WiFi está conectado
                    val isWifiConnected = NetworkUtils.isWifiConnected(applicationContext)
                    
                    if (isWifiConnected) {
                        Log.d(TAG, "WiFi conectado, tentando enviar via MQTT...")
                        success = mqttHelper.publishCurrentTime()
                        
                        if (success) {
                            Log.d(TAG, "✅ Envio bem-sucedido na tentativa $attemptCount")
                            notificationHelper.cancelAlertNotification()
                            break // Sair do loop se o envio foi bem-sucedido
                        } else {
                            Log.e(TAG, "❌ Falha no envio na tentativa $attemptCount")
                        }
                    } else {
                        Log.w(TAG, "⚠️ WiFi não conectado na tentativa $attemptCount")
                    }
                    
                    // Aguardar 5 segundos antes da próxima tentativa (exceto na última)
                    if (attemptCount < MQTT_MAX_RETRIES && !success) {
                        delay(MQTT_RETRY_DELAY)
                    }
                }
                
                if (success) {
                    Log.d(TAG, "✅ Processo de tentativas concluído com sucesso!")
                } else {
                    Log.w(TAG, "⚠️ Processo de tentativas finalizado sem sucesso após $attemptCount tentativas")
                }
                
            } catch (e: Exception) {
                Log.e(TAG, "Erro ao processar clique WiFi: ${e.message}", e)
            }
        }
    }
}
