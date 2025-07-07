package com.sae5g.mqttwearable.mqtt

import android.content.Context
import android.content.SharedPreferences
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import org.eclipse.paho.client.mqttv3.MqttClient
import org.eclipse.paho.client.mqttv3.MqttConnectOptions
import org.eclipse.paho.client.mqttv3.MqttException
import org.eclipse.paho.client.mqttv3.MqttMessage
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence
import org.eclipse.paho.client.mqttv3.IMqttActionListener
import org.eclipse.paho.client.mqttv3.IMqttDeliveryToken
import org.eclipse.paho.client.mqttv3.IMqttToken
import org.eclipse.paho.client.mqttv3.MqttCallback
import android.util.Log
import com.sae5g.mqttwearable.connectivity.WiFiConnectivityManager

class MqttHandler(private val context: Context) {
    private var client: MqttClient? = null
    private var isConnected = false
    private val prefs: SharedPreferences = context.getSharedPreferences("mqtt_prefs", Context.MODE_PRIVATE)
    private val wifiManager = WiFiConnectivityManager(context)
    
    companion object {
        private const val BROKER_URL_KEY = "broker_url"
        private const val DEFAULT_BROKER_URL = "tcp://192.168.68.102:1883"
    }

    // Salva o broker URL no cache
    fun saveBrokerUrl(brokerUrl: String) {
        prefs.edit().putString(BROKER_URL_KEY, brokerUrl).apply()
        Log.d("MqttHandler", "Broker URL saved to cache: $brokerUrl")
        
        // Verificar se foi salvo corretamente
        val savedUrl = prefs.getString(BROKER_URL_KEY, null)
        Log.d("MqttHandler", "Verification - URL in cache after save: $savedUrl")
    }

    // Recupera o broker URL do cache
    fun getCachedBrokerUrl(): String {
        val cachedUrl = prefs.getString(BROKER_URL_KEY, DEFAULT_BROKER_URL) ?: DEFAULT_BROKER_URL
        Log.d("MqttHandler", "Retrieved cached broker URL: $cachedUrl")
        return cachedUrl
    }

    // Conecta usando o broker URL do cache
    fun connectWithCachedUrl(clientId: String, callback: (Boolean) -> Unit) {
        val cachedBrokerUrl = getCachedBrokerUrl()
        Log.d("MqttHandler", "Connecting with cached URL: $cachedBrokerUrl")
        connect(cachedBrokerUrl, clientId, callback)
    }

    fun connect(brokerUrl: String, clientId: String, callback: (Boolean) -> Unit) {
        // Salva automaticamente o broker URL quando conecta
        saveBrokerUrl(brokerUrl)
        
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val persistence = MemoryPersistence()
                client = MqttClient(brokerUrl, clientId, persistence).apply {
                    val options = MqttConnectOptions().apply {
                        isCleanSession = true
                        connectionTimeout = 10
                        keepAliveInterval = 20
                    }
                    connect(options)
                }
                
                // Definir como conectado após sucesso na conexão
                isConnected = true
                Log.d("MqttHandler", "Connected to $brokerUrl")
                callback(true)
            } catch (e: MqttException) {
                Log.e("MqttHandler", "Connection failed", e)
                callback(false)
            }
        }
    }

    fun disconnect() {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                client?.disconnect()
                isConnected = false
                Log.d("MqttHandler", "Disconnected")
            } catch (e: MqttException) {
                Log.e("MqttHandler", "Disconnect failed", e)
            }
        }
    }

    fun publish(topic: String, message: String, encrypt: Boolean = true, callback: (Boolean) -> Unit = { _ -> }) {
        // Primeiro verificar conectividade WiFi
        checkConnectivityAndPublish(topic, message, encrypt, callback)
    }
    
    private fun checkConnectivityAndPublish(topic: String, message: String, encrypt: Boolean, callback: (Boolean) -> Unit) {
        CoroutineScope(Dispatchers.IO).launch {
            Log.d("MqttHandler", "Verificando conectividade antes de publicar...")
            
            // Extrair IP do servidor MQTT do broker URL
            val serverIp = extractServerIpFromBrokerUrl()
            
            if (serverIp == null) {
                Log.e("MqttHandler", "Não foi possível extrair IP do servidor MQTT")
                callback(false)
                return@launch
            }
            
            wifiManager.checkFullConnectivity(serverIp) { result ->
                when (result) {
                    WiFiConnectivityManager.ConnectivityResult.FULL_CONNECTIVITY -> {
                        Log.d("MqttHandler", "Conectividade WiFi+MQTT verificada, verificando cliente MQTT...")
                        
                        // Verificar se cliente MQTT está realmente conectado
                        val clientConnected = client?.isConnected ?: false
                        Log.d("MqttHandler", "Estado MQTT: isConnected=$isConnected, client.isConnected=$clientConnected")
                        
                        if (isConnected && clientConnected) {
                            Log.d("MqttHandler", "Cliente MQTT já conectado, publicando mensagem...")
                            performPublishDirect(topic, message, encrypt, callback)
                        } else {
                            Log.w("MqttHandler", "Servidor MQTT alcançável mas cliente não conectado, reconectando...")
                            attemptReconnection { reconnectSuccess ->
                                if (reconnectSuccess) {
                                    Log.d("MqttHandler", "Reconexão bem-sucedida, publicando mensagem...")
                                    performPublishDirect(topic, message, encrypt, callback)
                                } else {
                                    Log.e("MqttHandler", "Falha na reconexão MQTT")
                                    callback(false)
                                }
                            }
                        }
                    }
                    WiFiConnectivityManager.ConnectivityResult.WIFI_ONLY -> {
                        Log.w("MqttHandler", "WiFi conectado mas servidor MQTT não alcançável")
                        callback(false)
                    }
                    WiFiConnectivityManager.ConnectivityResult.NO_WIFI -> {
                        Log.w("MqttHandler", "Sem conexão WiFi disponível")
                        callback(false)
                    }
                }
            }
        }
    }
    
    private fun extractServerIpFromBrokerUrl(): String? {
        val brokerUrl = getCachedBrokerUrl()
        return try {
            // Formato: tcp://IP:1883
            brokerUrl.replace("tcp://", "").split(":")[0]
        } catch (e: Exception) {
            Log.e("MqttHandler", "Erro ao extrair IP do broker URL: $brokerUrl", e)
            null
        }
    }
    
    private fun performPublish(topic: String, message: String, encrypt: Boolean, callback: (Boolean) -> Unit) {
        if (!isConnected) {
            Log.w("MqttHandler", "MQTT não conectado, tentando reconectar...")
            // Tentar reconectar automaticamente
            attemptReconnection { reconnectSuccess ->
                if (reconnectSuccess) {
                    Log.d("MqttHandler", "Reconexão bem-sucedida, tentando publicar novamente...")
                    performPublish(topic, message, encrypt, callback)
                } else {
                    Log.e("MqttHandler", "Falha na reconexão MQTT")
                    callback(false)
                }
            }
            return
        }

        performPublishDirect(topic, message, encrypt, callback)
    }
    
    private fun performPublishDirect(topic: String, message: String, encrypt: Boolean, callback: (Boolean) -> Unit) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                // Criptografar a mensagem se solicitado
                val finalMessage = if (encrypt) {
                    val encryptedMessage = AESCrypto.encrypt(message)
                    if (encryptedMessage != null) {
                        encryptedMessage
                    } else {
                        Log.e("MqttHandler", "Failed to encrypt message, sending plain text")
                        message
                    }
                } else {
                    message
                }
                
                val mqttMessage = MqttMessage(finalMessage.toByteArray())
                client?.publish(topic, mqttMessage)
                
                if (encrypt) {
                    Log.d("MqttHandler", "Published encrypted message to $topic (original: $message)")
                } else {
                    Log.d("MqttHandler", "Published to $topic: $message")
                }
                callback(true)
            } catch (e: MqttException) {
                Log.e("MqttHandler", "Publish failed", e)
                callback(false)
            }
        }
    }

    fun subscribe(topic: String, callback: (String) -> Unit) {
        if (!isConnected) {
            Log.e("MqttHandler", "Not connected, cannot subscribe")
            return
        }

        CoroutineScope(Dispatchers.IO).launch {
            try {
                client?.setCallback(object : MqttCallback {
                    override fun connectionLost(cause: Throwable) {
                        Log.e("MqttHandler", "Connection lost", cause)
                        isConnected = false
                    }

                    override fun messageArrived(receivedTopic: String, receivedMessage: MqttMessage) {
                        val payload = String(receivedMessage.payload)
                        Log.d("MqttHandler", "Message arrived on $receivedTopic: $payload")
                        callback(payload)
                    }

                    override fun deliveryComplete(token: IMqttDeliveryToken) {
                        Log.d("MqttHandler", "Message delivered")
                    }
                })
                client?.subscribe(topic)
                Log.d("MqttHandler", "Subscribed to $topic")
            } catch (e: MqttException) {
                Log.e("MqttHandler", "Subscribe failed", e)
            }
        }
    }
    
    private fun attemptReconnection(callback: (Boolean) -> Unit) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                Log.d("MqttHandler", "Tentando reconexão automática...")
                
                // Desconectar cliente antigo se existir
                client?.let { oldClient ->
                    try {
                        if (oldClient.isConnected) {
                            oldClient.disconnect()
                        }
                        oldClient.close()
                    } catch (e: Exception) {
                        Log.w("MqttHandler", "Erro ao desconectar cliente antigo: ${e.message}")
                    }
                }
                
                // Tentar nova conexão usando URL em cache
                val cachedBrokerUrl = getCachedBrokerUrl()
                val clientId = "WearableClient_${System.currentTimeMillis()}"
                
                val persistence = MemoryPersistence()
                client = MqttClient(cachedBrokerUrl, clientId, persistence).apply {
                    val options = MqttConnectOptions().apply {
                        isCleanSession = true
                        connectionTimeout = 10
                        keepAliveInterval = 20
                    }
                    
                    // Configurar callback para detectar perda de conexão
                    setCallback(object : MqttCallback {
                        override fun connectionLost(cause: Throwable) {
                            Log.e("MqttHandler", "Conexão MQTT perdida novamente", cause)
                            this@MqttHandler.isConnected = false
                        }

                        override fun messageArrived(receivedTopic: String, receivedMessage: MqttMessage) {
                            Log.d("MqttHandler", "Mensagem recebida em $receivedTopic: ${String(receivedMessage.payload)}")
                        }

                        override fun deliveryComplete(token: IMqttDeliveryToken) {
                            Log.d("MqttHandler", "Mensagem entregue com sucesso")
                        }
                    })
                    
                    connect(options)
                }
                
                // Verificar se a conexão foi realmente estabelecida
                if (client?.isConnected == true) {
                    isConnected = true
                    Log.d("MqttHandler", "Reconexão MQTT bem-sucedida para $cachedBrokerUrl")
                    callback(true)
                } else {
                    isConnected = false
                    Log.e("MqttHandler", "Reconexão falhou - cliente não conectado")
                    callback(false)
                }
                
            } catch (e: MqttException) {
                Log.e("MqttHandler", "Falha na reconexão MQTT", e)
                isConnected = false
                callback(false)
            }
        }
    }
}
