package com.iagoBiundini.mqttwifi.presentation

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import com.iagoBiundini.mqttwifi.R
import com.iagoBiundini.mqttwifi.service.WifiMonitorService

class MainActivity : ComponentActivity() {
    
    private lateinit var countdownTextView: TextView
    private lateinit var sendNowButton: Button
    
    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        // Iniciar o serviço independentemente da permissão
        // (a permissão é importante mas não crítica)
        startWifiMonitorService()
    }
    
    private val countdownReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action == WifiMonitorService.ACTION_UPDATE_COUNTDOWN) {
                val secondsRemaining = intent.getIntExtra(
                    WifiMonitorService.EXTRA_SECONDS_REMAINING,
                    60
                )
                updateCountdown(secondsRemaining)
            }
        }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        
        setTheme(android.R.style.Theme_DeviceDefault)
        setContentView(R.layout.activity_main)
        
        countdownTextView = findViewById(R.id.countdownTextView)
        sendNowButton = findViewById(R.id.sendNowButton)
        
        // Configurar botão de envio manual
        sendNowButton.setOnClickListener {
            sendManualMqttRequest()
        }
        
        // Verificar e solicitar permissões
        checkAndRequestPermissions()
    }
    
    override fun onResume() {
        super.onResume()
        
        // Registrar o receiver para receber atualizações da contagem
        val filter = IntentFilter(WifiMonitorService.ACTION_UPDATE_COUNTDOWN)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(countdownReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            registerReceiver(countdownReceiver, filter)
        }
    }
    
    override fun onPause() {
        super.onPause()
        
        // Desregistrar o receiver
        try {
            unregisterReceiver(countdownReceiver)
        } catch (e: IllegalArgumentException) {
            // Receiver já foi desregistrado
        }
    }
    
    /**
     * Verifica e solicita permissões necessárias
     */
    private fun checkAndRequestPermissions() {
        // Permissão de notificação (necessária no Android 13+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            requestPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        } else {
            // Versões antigas não precisam da permissão, iniciar direto
            startWifiMonitorService()
        }
    }
    
    /**
     * Inicia o serviço de monitoramento WiFi
     */
    private fun startWifiMonitorService() {
        val serviceIntent = Intent(this, WifiMonitorService::class.java)
        ContextCompat.startForegroundService(this, serviceIntent)
    }
    
    /**
     * Atualiza o texto da contagem regressiva
     */
    private fun updateCountdown(seconds: Int) {
        countdownTextView.text = seconds.toString()
    }
    
    /**
     * Envia solicitação manual para envio MQTT
     */
    private fun sendManualMqttRequest() {
        val intent = Intent(WifiMonitorService.ACTION_SEND_NOW)
        sendBroadcast(intent)
        
        Toast.makeText(this, "Enviando dados...", Toast.LENGTH_SHORT).show()
    }
}
