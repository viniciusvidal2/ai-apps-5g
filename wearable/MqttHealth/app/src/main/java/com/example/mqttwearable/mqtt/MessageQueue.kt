package com.sae5g.mqttwearable.mqtt

import android.content.Context
import android.content.SharedPreferences
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.*

data class QueuedMessage(
    val id: String,
    val topic: String,
    val message: String,
    val encrypt: Boolean,
    val timestamp: String,
    val retryCount: Int = 0
)

class MessageQueue(private val context: Context) {
    private val prefs: SharedPreferences = context.getSharedPreferences("message_queue", Context.MODE_PRIVATE)
    
    companion object {
        private const val QUEUE_KEY = "pending_messages"
        private const val MAX_QUEUE_SIZE = 100
        private const val MAX_RETRY_COUNT = 3
        private const val TAG = "MessageQueue"
    }

    /**
     * Adiciona uma mensagem à fila
     */
    fun enqueue(topic: String, message: String, encrypt: Boolean = true): String {
        val messageId = generateMessageId()
        val timestamp = getCurrentTimestamp()
        
        val queuedMessage = QueuedMessage(
            id = messageId,
            topic = topic,
            message = message,
            encrypt = encrypt,
            timestamp = timestamp,
            retryCount = 0
        )
        
        val currentQueue = getQueuedMessages().toMutableList()
        
        // Verificar limite da fila - remover mensagens mais antigas se necessário
        if (currentQueue.size >= MAX_QUEUE_SIZE) {
            Log.w(TAG, "Fila cheia, removendo mensagens mais antigas...")
            // Remover mensagens mais antigas (primeiras da lista)
            val messagesToRemove = currentQueue.size - MAX_QUEUE_SIZE + 1
            repeat(messagesToRemove) {
                currentQueue.removeFirstOrNull()
            }
        }
        
        currentQueue.add(queuedMessage)
        saveQueuedMessages(currentQueue)
        
        Log.d(TAG, "Mensagem adicionada à fila: $messageId - Tópico: $topic - Total na fila: ${currentQueue.size}")
        return messageId
    }

    /**
     * Remove uma mensagem da fila por ID
     */
    fun dequeue(messageId: String): Boolean {
        val currentQueue = getQueuedMessages().toMutableList()
        val messageRemoved = currentQueue.removeAll { it.id == messageId }
        
        if (messageRemoved) {
            saveQueuedMessages(currentQueue)
            Log.d(TAG, "Mensagem removida da fila: $messageId - Total na fila: ${currentQueue.size}")
        } else {
            Log.w(TAG, "Mensagem não encontrada na fila: $messageId")
        }
        
        return messageRemoved
    }

    /**
     * Obtém todas as mensagens da fila
     */
    fun getQueuedMessages(): List<QueuedMessage> {
        return try {
            val queueJson = prefs.getString(QUEUE_KEY, "[]") ?: "[]"
            val jsonArray = JSONArray(queueJson)
            val messages = mutableListOf<QueuedMessage>()
            
            for (i in 0 until jsonArray.length()) {
                val jsonObject = jsonArray.getJSONObject(i)
                val message = QueuedMessage(
                    id = jsonObject.getString("id"),
                    topic = jsonObject.getString("topic"),
                    message = jsonObject.getString("message"),
                    encrypt = jsonObject.getBoolean("encrypt"),
                    timestamp = jsonObject.getString("timestamp"),
                    retryCount = jsonObject.optInt("retryCount", 0)
                )
                messages.add(message)
            }
            
            messages
        } catch (e: Exception) {
            Log.e(TAG, "Erro ao carregar mensagens da fila", e)
            emptyList()
        }
    }

    /**
     * Limpa todas as mensagens da fila
     */
    fun clearQueue() {
        prefs.edit().remove(QUEUE_KEY).apply()
        Log.d(TAG, "Fila de mensagens limpa")
    }

    /**
     * Obtém o número de mensagens na fila
     */
    fun getQueueSize(): Int {
        return getQueuedMessages().size
    }

    /**
     * Incrementa o contador de retry de uma mensagem
     */
    fun incrementRetryCount(messageId: String): Boolean {
        val currentQueue = getQueuedMessages().toMutableList()
        val messageIndex = currentQueue.indexOfFirst { it.id == messageId }
        
        if (messageIndex >= 0) {
            val message = currentQueue[messageIndex]
            val updatedMessage = message.copy(retryCount = message.retryCount + 1)
            
            // Verificar se excedeu o limite de tentativas
            if (updatedMessage.retryCount > MAX_RETRY_COUNT) {
                Log.w(TAG, "Mensagem excedeu limite de tentativas, removendo: $messageId")
                currentQueue.removeAt(messageIndex)
            } else {
                currentQueue[messageIndex] = updatedMessage
                Log.d(TAG, "Retry count incrementado para mensagem $messageId: ${updatedMessage.retryCount}")
            }
            
            saveQueuedMessages(currentQueue)
            return true
        }
        
        return false
    }

    /**
     * Obtém estatísticas da fila
     */
    fun getQueueStats(): Map<String, Any> {
        val messages = getQueuedMessages()
        return mapOf(
            "totalMessages" to messages.size,
            "oldestMessage" to (messages.minByOrNull { it.timestamp }?.timestamp ?: "N/A"),
            "newestMessage" to (messages.maxByOrNull { it.timestamp }?.timestamp ?: "N/A"),
            "topicDistribution" to messages.groupBy { it.topic }.mapValues { it.value.size }
        )
    }

    private fun saveQueuedMessages(messages: List<QueuedMessage>) {
        try {
            val jsonArray = JSONArray()
            
            messages.forEach { message ->
                val jsonObject = JSONObject().apply {
                    put("id", message.id)
                    put("topic", message.topic)
                    put("message", message.message)
                    put("encrypt", message.encrypt)
                    put("timestamp", message.timestamp)
                    put("retryCount", message.retryCount)
                }
                jsonArray.put(jsonObject)
            }
            
            prefs.edit().putString(QUEUE_KEY, jsonArray.toString()).apply()
        } catch (e: Exception) {
            Log.e(TAG, "Erro ao salvar mensagens na fila", e)
        }
    }

    private fun generateMessageId(): String {
        return "msg_${System.currentTimeMillis()}_${(1000..9999).random()}"
    }

    private fun getCurrentTimestamp(): String {
        val sdf = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
        sdf.timeZone = TimeZone.getTimeZone("UTC")
        return sdf.format(Date())
    }
} 