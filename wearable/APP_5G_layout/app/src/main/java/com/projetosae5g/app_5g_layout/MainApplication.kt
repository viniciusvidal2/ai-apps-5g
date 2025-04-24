package com.projetosae5g.app_5g_layout

import android.app.Application
import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.wifi.WifiManager
import android.net.wifi.WifiNetworkSpecifier
import android.net.NetworkRequest
import android.net.ConnectivityManager.NetworkCallback
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.util.Log

class MainApplication : Application() {
    
    lateinit var mqttHandler: MqttHandler
    private val publishHandler = Handler(Looper.getMainLooper())
    private var mqttPublishRunnable: Runnable? = null
    
    // Configurações Wi-Fi
    private val WIFI_SSID = "Grin"
    private val WIFI_PASSWORD = "grin1020"
    
    override fun onCreate() {
        super.onCreate()
        
        // Inicializar o handler MQTT com o IP salvo
        val sharedPreferences = getSharedPreferences("mqtt_settings", Context.MODE_PRIVATE)
        val savedIp = sharedPreferences.getString("server_ip", "192.168.0.120") ?: "192.168.0.120"
        
        mqttHandler = MqttHandler(applicationContext, savedIp)
        
        // Não tentar conectar automaticamente para evitar falhas na inicialização
        // A conexão será feita quando o usuário pressionar o botão conectar
    }
    
    // Verificar se está conectado ao Wi-Fi
    private fun isWifiConnected(): Boolean {
        val connectivityManager = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val network = connectivityManager.activeNetwork
            val capabilities = connectivityManager.getNetworkCapabilities(network)
            return capabilities != null && capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)
        } else {
            @Suppress("DEPRECATION")
            val networkInfo = connectivityManager.activeNetworkInfo
            return networkInfo != null && networkInfo.type == ConnectivityManager.TYPE_WIFI && networkInfo.isConnected
        }
    }
    
    // Verificar se está conectado à rede Wi-Fi desejada
    private fun isConnectedToDesiredWifi(): Boolean {
        val wifiManager = applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
        val wifiInfo = wifiManager.connectionInfo
        val ssid = wifiInfo?.ssid?.replace("\"", "") // Remove as aspas que o Android adiciona ao SSID
        
        return ssid == WIFI_SSID
    }
    
    // Conectar à rede Wi-Fi desejada (funcionalidade limitada em Android moderno)
    private fun connectToWifi() {
        try {
            Log.d("MainApplication", "Tentando conectar ao Wi-Fi: $WIFI_SSID")
            
            // Em versões mais recentes do Android, é necessário usar o NetworkRequest
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val wifiNetworkSpecifier = WifiNetworkSpecifier.Builder()
                    .setSsid(WIFI_SSID)
                    .setWpa2Passphrase(WIFI_PASSWORD)
                    .build()
                
                val networkRequest = NetworkRequest.Builder()
                    .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
                    .setNetworkSpecifier(wifiNetworkSpecifier)
                    .build()
                
                val connectivityManager = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
                
                val networkCallback = object : NetworkCallback() {
                    override fun onAvailable(network: android.net.Network) {
                        // Conexão estabelecida, agora podemos tentar conectar ao MQTT
                        Log.d("MainApplication", "Conectado à rede Wi-Fi: $WIFI_SSID")
                        
                        // Verificar conexão MQTT
                        if (!mqttHandler.isConnected()) {
                            try {
                                mqttHandler.connect()
                            } catch (e: Exception) {
                                Log.e("MainApplication", "Falha ao conectar MQTT após conexão Wi-Fi", e)
                            }
                        }
                    }
                    
                    override fun onUnavailable() {
                        Log.e("MainApplication", "Falha ao conectar à rede Wi-Fi: $WIFI_SSID")
                    }
                }
                
                connectivityManager.requestNetwork(networkRequest, networkCallback)
            } else {
                // Para versões antigas, apenas exibir um log informativo
                // Conexão direta ao Wi-Fi não é mais possível sem apps de sistema
                Log.d("MainApplication", "Conexão automática ao Wi-Fi não suportada nesta versão do Android. Por favor, conecte-se manualmente.")
            }
        } catch (e: Exception) {
            Log.e("MainApplication", "Erro ao tentar conectar ao Wi-Fi", e)
        }
    }
    
    // Iniciar a publicação periódica de medições (chamado pela MainActivity)
    fun startMqttPublishing(heartRateProvider: () -> Double?, batteryLevelProvider: () -> Int?, secondsMeasureProvider: () -> Long) {
        // Parar qualquer publicação existente
        stopMqttPublishing()
        
        mqttPublishRunnable = Runnable {
            // Verificar se há alguma conexão Wi-Fi
            if (!isWifiConnected()) {
                // Só tenta conectar se não houver conexão Wi-Fi alguma
                Log.d("MainApplication", "Wi-Fi não conectado. Tentando conectar...")
                connectToWifi()
            } else {
                // Wi-Fi já está conectado, não importa qual rede
                // Verificar conexão MQTT com o servidor atual
                if (mqttHandler.isConnected()) {
                    // Obter os dados mais recentes
                    val heartRate = heartRateProvider()
                    val batteryLevel = batteryLevelProvider()
                    val secondsMeasure = secondsMeasureProvider()
                    
                    // Publicar os dados
                    mqttHandler.publishMeasurements(heartRate, batteryLevel, secondsMeasure)
                    Log.d("MainApplication", "Dados MQTT publicados: HR=$heartRate, Bateria=$batteryLevel, Intervalo=$secondsMeasure")
                } else {
                    // Tentar reconectar o MQTT sem interferir na conexão Wi-Fi atual
                    Log.d("MainApplication", "Wi-Fi conectado, mas MQTT desconectado. Reconectando MQTT...")
                    try {
                        mqttHandler.connect()
                    } catch (e: Exception) {
                        Log.e("MainApplication", "Falha ao reconectar MQTT", e)
                    }
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