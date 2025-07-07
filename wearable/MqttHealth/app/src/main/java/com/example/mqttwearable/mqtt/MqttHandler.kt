package com.sae5g.mqttwearable.mqtt

import android.content.Context
import android.content.SharedPreferences
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.delay
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
    private val messageQueue = MessageQueue(context)
    
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
    
    /**
     * Tenta processar a fila quando WiFi reconectar
     */
    fun onWiFiReconnected() {
        CoroutineScope(Dispatchers.IO).launch {
            Log.d("MqttHandler", "🔄 WiFi reconectado, verificando fila de mensagens...")
            val queueSize = messageQueue.getQueueSize()
            val queueStats = messageQueue.getQueueStats()
            
            Log.d("MqttHandler", "📊 Status da fila: $queueSize mensagens | Stats: $queueStats")
            
            if (queueSize > 0) {
                Log.d("MqttHandler", "📥 Encontradas $queueSize mensagens na fila, iniciando processamento...")
                
                // Aguardar um pouco para estabilizar a conexão
                delay(1000)
                
                // Verificar se MQTT está conectado, senão tentar reconectar
                val mqttConnected = client?.isConnected ?: false
                Log.d("MqttHandler", "🔍 Estado MQTT: isConnected=$isConnected, client.isConnected=$mqttConnected")
                
                if (!isConnected || !mqttConnected) {
                    Log.d("MqttHandler", "🔌 MQTT não conectado, tentando reconectar primeiro...")
                    attemptReconnection { reconnectSuccess ->
                        if (reconnectSuccess) {
                            Log.d("MqttHandler", "✅ Reconexão MQTT bem-sucedida, fila será processada automaticamente")
                            // A fila será processada automaticamente pelo attemptReconnection
                        } else {
                            Log.w("MqttHandler", "❌ Falha na reconexão MQTT, tentando processar fila mesmo assim...")
                            // Tentar processar mesmo com falha na reconexão em uma nova coroutine
                            CoroutineScope(Dispatchers.IO).launch {
                                delay(2000) // Aguardar um pouco antes de tentar
                                tryProcessQueueAnyway()
                            }
                        }
                    }
                } else {
                    Log.d("MqttHandler", "✅ MQTT já conectado, processando fila diretamente...")
                    // Não precisa criar nova coroutine, já estamos em uma
                    processQueuedMessages { successCount, failureCount ->
                        Log.d("MqttHandler", "🎯 Resultado do processamento da fila: $successCount enviadas, $failureCount falharam")
                    }
                }
                
                // BACKUP: Aguardar 5 segundos e verificar se a fila ainda tem mensagens
                // Se tiver, tentar processar novamente
                delay(5000)
                val remainingMessages = messageQueue.getQueueSize()
                if (remainingMessages > 0) {
                    Log.w("MqttHandler", "⚠️ BACKUP: Ainda há $remainingMessages mensagens na fila após 5s, tentando novamente...")
                    // Não precisa criar nova coroutine, já estamos em uma
                    processQueuedMessages { successCount, failureCount ->
                        Log.d("MqttHandler", "🎯 Processamento BACKUP da fila: $successCount enviadas, $failureCount falharam")
                    }
                }
            } else {
                Log.d("MqttHandler", "📭 Nenhuma mensagem na fila para processar")
            }
        }
    }
    
    /**
     * Tenta processar a fila mesmo se MQTT não estiver perfeitamente conectado
     * NOTA: Esta função deve ser chamada apenas de dentro de um CoroutineScope
     */
    private suspend fun tryProcessQueueAnyway() {
        Log.d("MqttHandler", "🔄 Tentando processar fila mesmo com problemas de conexão...")
        processQueuedMessages { successCount, failureCount ->
            Log.d("MqttHandler", "🎯 Processamento forçado da fila: $successCount enviadas, $failureCount falharam")
            if (successCount == 0 && failureCount > 0) {
                Log.w("MqttHandler", "⚠️ Todas as mensagens falharam, verificar conectividade MQTT")
            }
        }
    }
    
    /**
     * Função de debug para forçar processamento da fila
     */
    fun debugProcessQueue(): String {
        val queueSize = messageQueue.getQueueSize()
        val stats = messageQueue.getQueueStats()
        
        Log.d("MqttHandler", "🐛 DEBUG: Forçando processamento da fila...")
        Log.d("MqttHandler", "🐛 DEBUG: Tamanho da fila: $queueSize")
        Log.d("MqttHandler", "🐛 DEBUG: Stats: $stats")
        Log.d("MqttHandler", "🐛 DEBUG: MQTT conectado: ${client?.isConnected}")
        Log.d("MqttHandler", "🐛 DEBUG: isConnected flag: $isConnected")
        
        if (queueSize > 0) {
            CoroutineScope(Dispatchers.IO).launch {
                processQueuedMessages { successCount, failureCount ->
                    Log.d("MqttHandler", "🐛 DEBUG: Resultado: $successCount enviadas, $failureCount falharam")
                }
            }
            return "Processando $queueSize mensagens da fila..."
        } else {
            return "Fila vazia"
        }
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
    
    /**
     * Obtém estatísticas da fila de mensagens
     */
    fun getQueueStats(): Map<String, Any> {
        return messageQueue.getQueueStats()
    }
    
    /**
     * Processa todas as mensagens na fila quando há conectividade
     * NOTA: Esta função deve ser chamada de dentro de um CoroutineScope
     */
    suspend fun processQueuedMessages(callback: (Int, Int) -> Unit = { _, _ -> }) {
        val queuedMessages = messageQueue.getQueuedMessages()
        if (queuedMessages.isEmpty()) {
            Log.d("MqttHandler", "Nenhuma mensagem na fila para processar")
            callback(0, 0)
            return
        }
            
            Log.d("MqttHandler", "🚀 INICIANDO processamento de ${queuedMessages.size} mensagens da fila...")
            var successCount = 0
            var failureCount = 0
            var processedCount = 0
            
            // Processar mensagens sequencialmente para evitar problemas de concorrência
            queuedMessages.forEachIndexed { index, queuedMessage ->
                Log.d("MqttHandler", "📤 [${index + 1}/${queuedMessages.size}] Enviando mensagem da fila: ${queuedMessage.id} - Tópico: ${queuedMessage.topic} - Retry: ${queuedMessage.retryCount}")
                
                // Verificar se cliente MQTT ainda está conectado antes de cada envio
                if (client?.isConnected != true) {
                    Log.w("MqttHandler", "❌ Cliente MQTT desconectado durante processamento da fila")
                    failureCount++
                    processedCount++
                    messageQueue.incrementRetryCount(queuedMessage.id)
                    
                    // Verificar se todas foram processadas
                    if (processedCount == queuedMessages.size) {
                        Log.d("MqttHandler", "✅ Processamento da fila concluído: $successCount sucessos, $failureCount falhas")
                        callback(successCount, failureCount)
                    }
                    return@forEachIndexed
                }
                
                performPublishDirect(queuedMessage.topic, queuedMessage.message, queuedMessage.encrypt) { success ->
                    processedCount++
                    
                    if (success) {
                        // Remover da fila se envio bem-sucedido
                        val removed = messageQueue.dequeue(queuedMessage.id)
                        successCount++
                        Log.d("MqttHandler", "✅ [${processedCount}/${queuedMessages.size}] Mensagem da fila enviada com sucesso: ${queuedMessage.id} (removida: $removed)")
                    } else {
                        // Incrementar contador de retry
                        val updated = messageQueue.incrementRetryCount(queuedMessage.id)
                        failureCount++
                        Log.w("MqttHandler", "❌ [${processedCount}/${queuedMessages.size}] Falha ao enviar mensagem da fila: ${queuedMessage.id} (retry atualizado: $updated)")
                    }
                    
                    // Callback final quando todas as mensagens foram processadas
                    if (processedCount == queuedMessages.size) {
                        Log.d("MqttHandler", "🏁 Processamento da fila concluído: $successCount sucessos, $failureCount falhas")
                        callback(successCount, failureCount)
                    }
                }
            }
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
                        Log.w("MqttHandler", "📶❌ WiFi conectado mas servidor MQTT não alcançável - adicionando à fila")
                        val messageId = messageQueue.enqueue(topic, message, encrypt)
                        val newQueueSize = messageQueue.getQueueSize()
                        Log.d("MqttHandler", "📥 Mensagem adicionada à fila: $messageId | Nova fila: $newQueueSize msgs | Tópico: $topic")
                        callback(false)
                    }
                    WiFiConnectivityManager.ConnectivityResult.NO_WIFI -> {
                        Log.w("MqttHandler", "📵 Sem conexão WiFi disponível - adicionando à fila")
                        val messageId = messageQueue.enqueue(topic, message, encrypt)
                        val newQueueSize = messageQueue.getQueueSize()
                        Log.d("MqttHandler", "📥 Mensagem adicionada à fila: $messageId | Nova fila: $newQueueSize msgs | Tópico: $topic")
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
                    
                    // Processar mensagens da fila após reconexão bem-sucedida
                    CoroutineScope(Dispatchers.IO).launch {
                        processQueuedMessages { successCount, failureCount ->
                            Log.d("MqttHandler", "🎯 Fila processada após reconexão MQTT: $successCount enviadas, $failureCount falharam")
                        }
                    }
                    
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
