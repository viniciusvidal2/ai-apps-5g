package com.iagoBiundini.mqttwifi.mqtt

import android.content.Context
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.eclipse.paho.client.mqttv3.MqttClient
import org.eclipse.paho.client.mqttv3.MqttConnectOptions
import org.eclipse.paho.client.mqttv3.MqttException
import org.eclipse.paho.client.mqttv3.MqttMessage
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MqttHelper(private val context: Context) {
    
    companion object {
        private const val TAG = "MqttHelper"
        private const val BROKER_URL = "tcp://192.168.0.112:1883"
        private const val TOPIC = "teste"
        private const val QOS = 1
        private const val CLIENT_ID = "WearOSClient"
    }
    
    private var mqttClient: MqttClient? = null
    private var isConnected = false
    
    /**
     * Conecta ao broker MQTT
     */
    private fun connect(): Boolean {
        return try {
            if (mqttClient?.isConnected == true) {
                Log.d(TAG, "Cliente já conectado")
                return true
            }
            
            val persistence = MemoryPersistence()
            mqttClient = MqttClient(BROKER_URL, CLIENT_ID, persistence).apply {
                val options = MqttConnectOptions().apply {
                    isCleanSession = true
                    connectionTimeout = 10
                    keepAliveInterval = 20
                }
                connect(options)
            }
            
            isConnected = true
            Log.d(TAG, "Conectado ao broker MQTT: $BROKER_URL")
            true
            
        } catch (e: MqttException) {
            Log.e(TAG, "Erro ao conectar ao MQTT: ${e.message}", e)
            isConnected = false
            false
        } catch (e: Exception) {
            Log.e(TAG, "Erro inesperado ao conectar: ${e.message}", e)
            isConnected = false
            false
        }
    }
    
    /**
     * Publica uma mensagem com o horário atual no tópico "teste"
     * Esta função deve ser chamada de um Dispatcher.IO
     */
    suspend fun publishCurrentTime(): Boolean = withContext(Dispatchers.IO) {
        try {
            if (!connect()) {
                Log.e(TAG, "Não foi possível conectar ao broker")
                return@withContext false
            }
            
            // Formata o horário atual
            val dateFormat = SimpleDateFormat("dd/MM/yyyy HH:mm:ss", Locale.getDefault())
            val currentTime = dateFormat.format(Date())
            
            val message = MqttMessage(currentTime.toByteArray()).apply {
                qos = QOS
            }
            
            mqttClient?.publish(TOPIC, message)
            Log.d(TAG, "Mensagem publicada no tópico '$TOPIC': $currentTime")
            
            true
            
        } catch (e: MqttException) {
            Log.e(TAG, "Erro ao publicar mensagem: ${e.message}", e)
            isConnected = false
            false
        } catch (e: Exception) {
            Log.e(TAG, "Erro inesperado ao publicar: ${e.message}", e)
            isConnected = false
            false
        }
    }
    
    /**
     * Desconecta do broker MQTT
     */
    fun disconnect() {
        try {
            mqttClient?.disconnect()
            mqttClient?.close()
            isConnected = false
            Log.d(TAG, "Desconectado do broker MQTT")
        } catch (e: MqttException) {
            Log.e(TAG, "Erro ao desconectar: ${e.message}", e)
        } catch (e: Exception) {
            Log.e(TAG, "Erro ao desconectar: ${e.message}", e)
        }
    }
    
    /**
     * Verifica se está conectado
     */
    fun isConnected(): Boolean {
        return mqttClient?.isConnected == true && isConnected
    }
}
