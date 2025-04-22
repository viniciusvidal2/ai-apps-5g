package com.projetosae5g.app_5g_layout

import android.content.Context
import android.util.Log
import org.eclipse.paho.client.mqttv3.*
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence
import org.json.JSONObject
import java.util.*

class MqttHandler(
    private val context: Context,
    private var serverIp: String = "192.168.0.120",
    private val port: Int = 1883
) {
    private val TAG = "MqttHandler"
    private var mqttClient: MqttAsyncClient? = null
    private var clientId = "WearOS_" + UUID.randomUUID().toString()
    private var isConnected = false
    
    // Interface para ouvintes de status da conexão
    interface ConnectionStatusListener {
        fun onConnectionStatusChanged(connected: Boolean)
    }
    
    private val connectionStatusListeners = mutableListOf<ConnectionStatusListener>()
    
    // Adicionar um ouvinte de status
    fun addConnectionStatusListener(listener: ConnectionStatusListener) {
        connectionStatusListeners.add(listener)
    }
    
    // Remover um ouvinte de status
    fun removeConnectionStatusListener(listener: ConnectionStatusListener) {
        connectionStatusListeners.remove(listener)
    }
    
    // Notificar todos os ouvintes sobre a mudança de status
    private fun notifyConnectionStatusChanged() {
        connectionStatusListeners.forEach { it.onConnectionStatusChanged(isConnected) }
    }
    
    // Atualizar o IP do servidor
    fun updateServerIp(newIp: String) {
        if (serverIp != newIp) {
            serverIp = newIp
            // Se já estava conectado, reconecta com o novo IP
            if (isConnected) {
                disconnect()
                connect()
            }
        }
    }
    
    // Verificar se está conectado
    fun isConnected(): Boolean {
        return isConnected
    }
    
    // Conectar ao servidor MQTT
    fun connect() {
        try {
            // Configurar endereço do servidor
            val serverUri = "tcp://$serverIp:$port"
            
            // Se existe conexão prévia, desconectar
            if (mqttClient != null && mqttClient!!.isConnected) {
                mqttClient!!.disconnect()
            }
            
            // Criar cliente MQTT assíncrono
            mqttClient = MqttAsyncClient(serverUri, clientId, MemoryPersistence())
            
            // Definir callback para eventos do MQTT
            mqttClient!!.setCallback(object : MqttCallback {
                override fun connectionLost(cause: Throwable?) {
                    Log.d(TAG, "Conexão MQTT perdida", cause)
                    isConnected = false
                    notifyConnectionStatusChanged()
                }
                
                override fun messageArrived(topic: String?, message: MqttMessage?) {
                    Log.d(TAG, "Mensagem recebida: $topic - ${message?.toString()}")
                }
                
                override fun deliveryComplete(token: IMqttDeliveryToken?) {
                    Log.d(TAG, "Entrega completa")
                }
            })
            
            // Opções de conexão
            val options = MqttConnectOptions().apply {
                isCleanSession = true
                connectionTimeout = 30
                keepAliveInterval = 60
                isAutomaticReconnect = true
            }
            
            // Conectar de forma assíncrona
            mqttClient!!.connect(options, null, object : IMqttActionListener {
                override fun onSuccess(asyncActionToken: IMqttToken?) {
                    Log.d(TAG, "Conexão MQTT estabelecida com sucesso")
                    isConnected = true
                    notifyConnectionStatusChanged()
                }
                
                override fun onFailure(asyncActionToken: IMqttToken?, exception: Throwable?) {
                    Log.e(TAG, "Falha ao conectar ao servidor MQTT", exception)
                    isConnected = false
                    notifyConnectionStatusChanged()
                }
            })
        } catch (e: Exception) {
            Log.e(TAG, "Erro ao conectar ao servidor MQTT", e)
            isConnected = false
            notifyConnectionStatusChanged()
        }
    }
    
    // Desconectar do servidor MQTT
    fun disconnect() {
        try {
            mqttClient?.let { client ->
                if (client.isConnected) {
                    client.disconnect(null, object : IMqttActionListener {
                        override fun onSuccess(asyncActionToken: IMqttToken?) {
                            Log.d(TAG, "Desconectado do servidor MQTT")
                            isConnected = false
                            notifyConnectionStatusChanged()
                        }
                        
                        override fun onFailure(asyncActionToken: IMqttToken?, exception: Throwable?) {
                            Log.e(TAG, "Erro ao desconectar do servidor MQTT", exception)
                        }
                    })
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Erro ao desconectar do servidor MQTT", e)
        } finally {
            mqttClient = null
            isConnected = false
            notifyConnectionStatusChanged()
        }
    }
    
    // Publicar dados de medições
    fun publishMeasurements(heartRate: Double?, batteryLevel: Int?, secondsMeasure: Long) {
        if (!isConnected || mqttClient == null) {
            Log.e(TAG, "Não é possível publicar: cliente não conectado")
            return
        }
        
        try {
            // Obter hora atual
            val currentTimestamp = System.currentTimeMillis()
            
            val jsonPayload = JSONObject().apply {
                put("heart_rate", heartRate ?: 0)
                put("battery", batteryLevel ?: 0)
                put("seconds_measure", secondsMeasure)
                put("date", java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss", 
                    java.util.Locale.getDefault()).format(java.util.Date(currentTimestamp)))
            }
            
            val payload = jsonPayload.toString().toByteArray()
            val message = MqttMessage(payload).apply {
                qos = 1
                isRetained = false
            }
            
            mqttClient!!.publish("measure", message, null, object : IMqttActionListener {
                override fun onSuccess(asyncActionToken: IMqttToken?) {
                    Log.d(TAG, "Dados publicados com sucesso: $jsonPayload")
                }
                
                override fun onFailure(asyncActionToken: IMqttToken?, exception: Throwable?) {
                    Log.e(TAG, "Erro ao publicar dados", exception)
                }
            })
        } catch (e: Exception) {
            Log.e(TAG, "Erro ao publicar dados", e)
        }
    }
} 