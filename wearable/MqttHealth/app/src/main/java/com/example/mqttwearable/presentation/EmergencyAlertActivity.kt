package com.example.mqttwearable.presentation

import android.content.Context
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.Vibrator
import android.util.Log
import android.view.View
import android.view.WindowManager
import android.widget.Button
import android.widget.TextView
import androidx.activity.ComponentActivity
import com.example.mqttwearable.R
import com.example.mqttwearable.mqtt.MqttHandler
import com.example.mqttwearable.data.DeviceIdManager
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

class EmergencyAlertActivity : ComponentActivity() {
    
    private lateinit var txtCountdownBig: TextView
    private lateinit var btnCancelEmergency: Button
    private lateinit var txtEmergencyMessage: TextView
    
    private lateinit var vibrator: Vibrator
    private lateinit var mqttHandler: MqttHandler
    private var alertHandler: Handler? = null
    private var alertCountdown = 10 // 10 segundos para cancelar
    private var isAlertActive = false
    
    // Localização recebida do MainActivity
    private var currentLatitude: Double? = null
    private var currentLongitude: Double? = null
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Manter tela ligada e em tela cheia
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        window.addFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN)
        
        setContentView(R.layout.activity_emergency_alert)
        
        // Inicializar views
        txtCountdownBig = findViewById(R.id.txtCountdownBig)
        btnCancelEmergency = findViewById(R.id.btnCancelEmergency)
        txtEmergencyMessage = findViewById(R.id.txtEmergencyMessage)
        
        // Receber dados de localização do MainActivity
        currentLatitude = intent.getDoubleExtra("CURRENT_LATITUDE", 0.0)
        currentLongitude = intent.getDoubleExtra("CURRENT_LONGITUDE", 0.0)
        
        // Ajustar para null se valores são 0.0 (não foram passados)
        if (currentLatitude == 0.0) currentLatitude = null
        if (currentLongitude == 0.0) currentLongitude = null
        
        // Inicializar componentes
        vibrator = getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
        mqttHandler = MqttHandler(applicationContext)
        
        // Configurar botão de cancelar
        btnCancelEmergency.setOnClickListener {
            cancelEmergencyAlert()
        }
        
        // Iniciar alerta imediatamente
        startEmergencyAlert()
    }
    
    private fun startEmergencyAlert() {
        if (isAlertActive) return
        
        isAlertActive = true
        alertCountdown = 10
        
        // Atualizar display
        updateCountdownDisplay()
        
        // Iniciar vibração e countdown
        startVibrationAndCountdown()
    }
    
    private fun updateCountdownDisplay() {
        txtCountdownBig.text = alertCountdown.toString()
        txtEmergencyMessage.text = "QUEDA DETECTADA!\nEnviando alerta em:"
    }
    
    private fun startVibrationAndCountdown() {
        alertHandler = Handler(Looper.getMainLooper())
        
        val vibrationRunnable = object : Runnable {
            override fun run() {
                if (isAlertActive && alertCountdown > 0) {
                    // Vibrar
                    if (vibrator.hasVibrator()) {
                        vibrator.vibrate(500) // Vibra por 500ms
                    }
                    
                    // Atualizar countdown
                    updateCountdownDisplay()
                    alertCountdown--
                    
                    // Agendar próxima vibração
                    alertHandler?.postDelayed(this, 1000)
                } else if (isAlertActive && alertCountdown <= 0) {
                    // Tempo esgotado - enviar alerta
                    sendEmergencyAlert()
                }
            }
        }
        
        alertHandler?.post(vibrationRunnable)
    }
    
    private fun sendEmergencyAlert() {
        // Criar JSON com horário atual em formato ISO 8601 UTC
        val sdf = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
        sdf.timeZone = TimeZone.getTimeZone("UTC")
        val currentTime = sdf.format(Date())
        
        // Criar JSON com Device ID, localização e dados de queda
        val emergencyMessage = buildString {
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
        
        // Usar o broker URL do cache
        val cachedBrokerUrl = mqttHandler.getCachedBrokerUrl()
        mqttHandler.connectWithCachedUrl("emergency-alert-${System.currentTimeMillis()}") { connected ->
            if (connected) {
                // Enviar mensagem MQTT para o tópico /fall
                mqttHandler.publish("/fall", emergencyMessage) { success ->
                    runOnUiThread {
                        if (success) {
                            txtEmergencyMessage.text = "ALERTA DE EMERGÊNCIA ENVIADO!"
                            txtCountdownBig.text = "0"
                        } else {
                            txtEmergencyMessage.text = "ERRO AO ENVIAR ALERTA!"
                            txtCountdownBig.text = "0"
                        }

                        // Fechar activity após 3 segundos
                        Handler(Looper.getMainLooper()).postDelayed({
                            finish()
                        }, 0)
                    }
                }
            } else {
                runOnUiThread {
                    txtEmergencyMessage.text = "ERRO DE CONEXÃO MQTT!"
                    txtCountdownBig.text = "0"
                    
                    // Fechar activity após 3 segundos
                    Handler(Looper.getMainLooper()).postDelayed({
                        finish()
                    }, 3000)
                }
            }
        }
        
        // Parar vibração
        vibrator.cancel()
        isAlertActive = false
        
        Log.d("EmergencyAlert", "Emergency alert sent: $emergencyMessage")
    }
    
    private fun cancelEmergencyAlert() {
        isAlertActive = false
        alertHandler?.removeCallbacksAndMessages(null)
        
        // Parar vibração
        vibrator.cancel()

        // Mostrar mensagem de cancelamento
        txtEmergencyMessage.text = "ALERTA CANCELADO"
        txtCountdownBig.text = "✓"

        Log.d("EmergencyAlert", "Emergency alert cancelled by user")

        // Fechar activity após 2 segundos
        Handler(Looper.getMainLooper()).postDelayed({
            finish()
        }, 0)
    }
    
    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        // Tratar botão voltar como cancelamento
        if (isAlertActive) {
            cancelEmergencyAlert()
        } else {
            super.onBackPressed()
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        // Limpar recursos
        if (isAlertActive) {
            cancelEmergencyAlert()
        }
        alertHandler?.removeCallbacksAndMessages(null)
    }
} 