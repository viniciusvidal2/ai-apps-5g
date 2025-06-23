package com.projetosae5g.app_5g_layout

import android.content.Context
import android.content.SharedPreferences
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.activity.ComponentActivity

class MqttConfigActivity : ComponentActivity(), MqttHandler.ConnectionStatusListener {
    
    private lateinit var editTextServerIp: EditText
    private lateinit var textViewConnectionStatus: TextView
    private lateinit var buttonConnect: Button
    private lateinit var buttonTestConnection: Button
    private lateinit var buttonSave: Button
    
    private lateinit var sharedPreferences: SharedPreferences
    private lateinit var mqttHandler: MqttHandler
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_mqtt_config)
        
        // Inicializar referências de UI
        editTextServerIp = findViewById(R.id.editTextServerIp)
        textViewConnectionStatus = findViewById(R.id.textViewConnectionStatus)
        buttonConnect = findViewById(R.id.buttonConnect)
        buttonTestConnection = findViewById(R.id.buttonTestConnection)
        buttonSave = findViewById(R.id.buttonSave)
        
        // Inicializar SharedPreferences
        sharedPreferences = getSharedPreferences("mqtt_settings", Context.MODE_PRIVATE)
        
        // Carregar o IP salvo
        val savedIp = sharedPreferences.getString("server_ip", "192.168.0.120")
        editTextServerIp.setText(savedIp)
        
        // Inicializar MqttHandler
        mqttHandler = (application as MainApplication).mqttHandler
        mqttHandler.addConnectionStatusListener(this)
        
        // Atualizar UI com status de conexão atual
        updateConnectionStatus(mqttHandler.isConnected())
        
        // Configurar botão de conexão
        buttonConnect.setOnClickListener {
            val ip = editTextServerIp.text.toString().trim()
            if (ip.isNotEmpty()) {
                if (mqttHandler.isConnected()) {
                    try {
                        mqttHandler.disconnect()
                        buttonConnect.text = "Conectar"
                    } catch (e: Exception) {
                        Log.e("MqttConfigActivity", "Erro ao desconectar", e)
                        Toast.makeText(this, "Erro ao desconectar: ${e.message}", Toast.LENGTH_SHORT).show()
                    }
                } else {
                    mqttHandler.updateServerIp(ip)
                    try {
                        mqttHandler.connect()
                        buttonConnect.text = "Desconectar"
                    } catch (e: Exception) {
                        Log.e("MqttConfigActivity", "Erro ao conectar", e)
                        Toast.makeText(this, "Erro ao conectar: ${e.message}", Toast.LENGTH_SHORT).show()
                    }
                }
            }
        }
        
        // Configurar botão de teste de conexão
        buttonTestConnection.setOnClickListener {
            val ip = editTextServerIp.text.toString().trim()
            if (ip.isNotEmpty()) {
                // Atualizar IP e tentar conectar temporariamente
                mqttHandler.updateServerIp(ip)
                Toast.makeText(this, "Testando conexão com $ip...", Toast.LENGTH_SHORT).show()
                
                try {
                    // Se já estiver conectado, desconecta primeiro para testar novamente
                    if (mqttHandler.isConnected()) {
                        mqttHandler.disconnect()
                    }
                    
                    // Tentar conectar
                    mqttHandler.connect()
                    
                    // Mostrar resultado (o status será atualizado pelo listener)
                    Toast.makeText(this, "Conexão iniciada, aguarde...", Toast.LENGTH_SHORT).show()
                } catch (e: Exception) {
                    Log.e("MqttConfigActivity", "Erro ao testar conexão", e)
                    Toast.makeText(this, "Erro ao testar: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
        
        // Configurar botão de salvar
        buttonSave.setOnClickListener {
            val ip = editTextServerIp.text.toString().trim()
            if (ip.isNotEmpty()) {
                // Salvar nas preferências
                sharedPreferences.edit().putString("server_ip", ip).apply()
                
                // Atualizar o handler MQTT
                mqttHandler.updateServerIp(ip)
                
                Toast.makeText(this, "Configuração salva", Toast.LENGTH_SHORT).show()
                
                // Voltar para a tela anterior
                finish()
            }
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        mqttHandler.removeConnectionStatusListener(this)
    }
    
    override fun onConnectionStatusChanged(connected: Boolean) {
        updateConnectionStatus(connected)
    }
    
    private fun updateConnectionStatus(connected: Boolean) {
        runOnUiThread {
            if (connected) {
                textViewConnectionStatus.text = "Conectado"
                textViewConnectionStatus.setTextColor(resources.getColor(android.R.color.holo_green_light, theme))
                buttonConnect.text = "Desconectar"
            } else {
                textViewConnectionStatus.text = "Desconectado"
                textViewConnectionStatus.setTextColor(resources.getColor(android.R.color.holo_red_light, theme))
                buttonConnect.text = "Conectar"
            }
        }
    }
} 