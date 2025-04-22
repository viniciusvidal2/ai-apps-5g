package com.projetosae5g.app_5g_layout

import android.app.Application
import android.content.Context
import android.os.Handler
import android.os.Looper
import android.util.Log

class MainApplication : Application() {
    
    lateinit var mqttHandler: MqttHandler
    private val publishHandler = Handler(Looper.getMainLooper())
    private var mqttPublishRunnable: Runnable? = null
    
    override fun onCreate() {
        super.onCreate()
        
        // Inicializar o handler MQTT com o IP salvo
        val sharedPreferences = getSharedPreferences("mqtt_settings", Context.MODE_PRIVATE)
        val savedIp = sharedPreferences.getString("server_ip", "192.168.0.120") ?: "192.168.0.120"
        
        mqttHandler = MqttHandler(applicationContext, savedIp)
        
        // Não tentar conectar automaticamente para evitar falhas na inicialização
        // A conexão será feita quando o usuário pressionar o botão conectar
    }
    
    // Iniciar a publicação periódica de medições (chamado pela MainActivity)
    fun startMqttPublishing(heartRateProvider: () -> Double?, batteryLevelProvider: () -> Int?, secondsMeasureProvider: () -> Long) {
        // Parar qualquer publicação existente
        stopMqttPublishing()
        
        mqttPublishRunnable = Runnable {
            if (mqttHandler.isConnected()) {
                // Obter os dados mais recentes
                val heartRate = heartRateProvider()
                val batteryLevel = batteryLevelProvider()
                val secondsMeasure = secondsMeasureProvider()
                
                // Publicar os dados
                mqttHandler.publishMeasurements(heartRate, batteryLevel, secondsMeasure)
                Log.d("MainApplication", "Dados MQTT publicados: HR=$heartRate, Bateria=$batteryLevel, Intervalo=$secondsMeasure")
            } else {
                // Tentar reconectar se desconectado
                Log.d("MainApplication", "Reconectando MQTT...")
                try {
                    mqttHandler.connect()
                } catch (e: Exception) {
                    Log.e("MainApplication", "Falha ao reconectar MQTT", e)
                }
            }
            
            // Agendar próxima publicação em 60 segundos
            publishHandler.postDelayed(mqttPublishRunnable!!, 60 * 1000)
        }
        
        // Iniciar o ciclo de publicação
        publishHandler.post(mqttPublishRunnable!!)
    }
    
    // Parar a publicação periódica
    fun stopMqttPublishing() {
        mqttPublishRunnable?.let {
            publishHandler.removeCallbacks(it)
            mqttPublishRunnable = null
        }
    }
    
    override fun onTerminate() {
        stopMqttPublishing()
        if (mqttHandler.isConnected()) {
            mqttHandler.disconnect()
        }
        super.onTerminate()
    }
} 