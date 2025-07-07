package com.sae5g.mqttwearable.connectivity

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.net.wifi.WifiManager
import android.net.wifi.WifiConfiguration
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.delay
import java.net.Socket
import java.net.InetSocketAddress

class WiFiConnectivityManager(private val context: Context) {
    
    private val wifiManager: WifiManager by lazy {
        context.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
    }
    
    private val connectivityManager: ConnectivityManager by lazy {
        context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
    }
    
    companion object {
        private const val TAG = "WiFiConnectivityManager"
        private const val CONNECTION_TIMEOUT = 5000 // 5 segundos
    }
    
    interface WiFiStatusListener {
        fun onWiFiStatusChanged(isConnected: Boolean, networkName: String?)
        fun onMqttServerReachable(isReachable: Boolean, serverIp: String)
        fun onError(message: String)
    }
    
    private var statusListener: WiFiStatusListener? = null
    
    fun setStatusListener(listener: WiFiStatusListener) {
        statusListener = listener
    }
    
    /**
     * Verifica se há conexão WiFi ativa
     */
    fun isWiFiConnected(): Boolean {
        return try {
            val network = connectivityManager.activeNetwork ?: return false
            val capabilities = connectivityManager.getNetworkCapabilities(network) ?: return false
            
            val isWiFi = capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)
            val hasInternet = capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            val validated = capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
            
            Log.d(TAG, "WiFi Connected: $isWiFi, Has Internet: $hasInternet, Validated: $validated")
            
            // Verificar se WiFi está conectado e tem pelo menos capacidade de internet
            // A validação pode não estar disponível imediatamente em algumas redes
            isWiFi && hasInternet
        } catch (e: Exception) {
            Log.e(TAG, "Erro ao verificar conexão WiFi", e)
            false
        }
    }
    
    /**
     * Verifica se o WiFi está conectado mas sem internet válido
     */
    fun isWiFiConnectedWithoutInternet(): Boolean {
        return try {
            val network = connectivityManager.activeNetwork ?: return false
            val capabilities = connectivityManager.getNetworkCapabilities(network) ?: return false
            
            val isWiFi = capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)
            val hasInternet = capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            val validated = capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED)
            
            // WiFi conectado mas sem internet ou não validado
            isWiFi && (!hasInternet || !validated)
        } catch (e: Exception) {
            Log.e(TAG, "Erro ao verificar conexão WiFi sem internet", e)
            false
        }
    }
    
    /**
     * Obtém o nome da rede WiFi atual
     */
    fun getCurrentNetworkName(): String? {
        return try {
            val connectionInfo = wifiManager.connectionInfo
            val ssid = connectionInfo?.ssid
            // Remover aspas do SSID se existirem
            ssid?.replace("\"", "")
        } catch (e: Exception) {
            Log.e(TAG, "Erro ao obter nome da rede", e)
            null
        }
    }
    
    /**
     * Verifica se o servidor MQTT é alcançável via WiFi
     */
    fun checkMqttServerReachability(serverIp: String, port: Int = 1883, callback: (Boolean) -> Unit) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val socket = Socket()
                socket.connect(InetSocketAddress(serverIp, port), CONNECTION_TIMEOUT)
                socket.close()
                
                Log.d(TAG, "Servidor MQTT alcançável: $serverIp:$port")
                callback(true)
                statusListener?.onMqttServerReachable(true, serverIp)
            } catch (e: Exception) {
                Log.e(TAG, "Servidor MQTT não alcançável: $serverIp:$port", e)
                callback(false)
                statusListener?.onMqttServerReachable(false, serverIp)
            }
        }
    }
    
    /**
     * Tenta conectar a uma rede WiFi conhecida
     */
    fun attemptConnectionToKnownNetworks(callback: (Boolean) -> Unit) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                if (!wifiManager.isWifiEnabled) {
                    Log.d(TAG, "WiFi está desabilitado, tentando habilitar...")
                    // Nota: Em Android 10+, apps não podem habilitar WiFi programaticamente
                    // Mas podemos verificar se foi habilitado pelo usuário
                    statusListener?.onError("WiFi desabilitado. Habilite manualmente.")
                    callback(false)
                    return@launch
                }
                
                // Verificar se já está conectado
                if (isWiFiConnected()) {
                    val networkName = getCurrentNetworkName()
                    Log.d(TAG, "Já conectado à rede: $networkName")
                    statusListener?.onWiFiStatusChanged(true, networkName)
                    callback(true)
                    return@launch
                }
                
                // Tentar reconectar às redes conhecidas
                val configuredNetworks = wifiManager.configuredNetworks
                if (configuredNetworks.isNullOrEmpty()) {
                    Log.d(TAG, "Nenhuma rede WiFi conhecida encontrada")
                    statusListener?.onError("Nenhuma rede WiFi conhecida")
                    callback(false)
                    return@launch
                }
                
                Log.d(TAG, "Tentando reconectar a redes conhecidas...")
                
                // Aguardar alguns segundos para possível reconexão automática
                repeat(10) { attempt ->
                    delay(1000)
                    if (isWiFiConnected()) {
                        val networkName = getCurrentNetworkName()
                        Log.d(TAG, "Conectado automaticamente à rede: $networkName")
                        statusListener?.onWiFiStatusChanged(true, networkName)
                        callback(true)
                        return@launch
                    }
                    Log.d(TAG, "Tentativa ${attempt + 1}/10 - Aguardando conexão...")
                }
                
                Log.d(TAG, "Falha ao conectar automaticamente às redes conhecidas")
                statusListener?.onWiFiStatusChanged(false, null)
                callback(false)
                
            } catch (e: Exception) {
                Log.e(TAG, "Erro ao tentar conectar a redes conhecidas", e)
                statusListener?.onError("Erro ao conectar: ${e.message}")
                callback(false)
            }
        }
    }
    
    /**
     * Verifica conectividade completa: WiFi + MQTT Server
     */
    fun checkFullConnectivity(mqttServerIp: String, callback: (ConnectivityResult) -> Unit) {
        CoroutineScope(Dispatchers.IO).launch {
            Log.d(TAG, "Verificando conectividade completa...")
            
            // 1. Verificar WiFi
            if (!isWiFiConnected()) {
                Log.d(TAG, "Sem conexão WiFi, tentando conectar...")
                
                attemptConnectionToKnownNetworks { wifiSuccess ->
                    if (wifiSuccess) {
                        // WiFi conectado, verificar MQTT
                        checkMqttServerReachability(mqttServerIp) { mqttReachable ->
                            val result = if (mqttReachable) {
                                ConnectivityResult.FULL_CONNECTIVITY
                            } else {
                                ConnectivityResult.WIFI_ONLY
                            }
                            callback(result)
                        }
                    } else {
                        callback(ConnectivityResult.NO_WIFI)
                    }
                }
            } else {
                // WiFi já conectado, verificar MQTT
                val networkName = getCurrentNetworkName()
                Log.d(TAG, "WiFi conectado à rede: $networkName")
                
                checkMqttServerReachability(mqttServerIp) { mqttReachable ->
                    val result = if (mqttReachable) {
                        ConnectivityResult.FULL_CONNECTIVITY
                    } else {
                        ConnectivityResult.WIFI_ONLY
                    }
                    callback(result)
                }
            }
        }
    }
    
    enum class ConnectivityResult {
        FULL_CONNECTIVITY,  // WiFi + MQTT Server alcançável
        WIFI_ONLY,          // WiFi conectado mas MQTT Server não alcançável
        NO_WIFI             // Sem WiFi
    }
} 