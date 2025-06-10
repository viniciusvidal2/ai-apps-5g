package com.example.mqttwearable.presentation

import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.lifecycle.lifecycleScope
import com.example.mqttwearable.health.BloodPressureManager
import com.example.mqttwearable.health.HealthPublisher
import com.example.mqttwearable.mqtt.MqttHandler
import kotlinx.coroutines.launch

class BloodPressureActivity : ComponentActivity() {
    
    private lateinit var bloodPressureManager: BloodPressureManager
    private lateinit var mqttHandler: MqttHandler
    private lateinit var healthPublisher: HealthPublisher
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Inicializa os managers
        bloodPressureManager = BloodPressureManager(this)
        bloodPressureManager.initialize()
        
        mqttHandler = MqttHandler(this)
        healthPublisher = HealthPublisher(this, mqttHandler)
        
        // Simula inserção de dados de pressão arterial para teste
        simulateBloodPressureData()
    }
    
    private fun simulateBloodPressureData() {
        lifecycleScope.launch {
            // Aguarda um pouco para a conexão ser estabelecida
            kotlinx.coroutines.delay(2000)
            
            // Dados de exemplo
            val systolic = 120f
            val diastolic = 80f
            val mean = bloodPressureManager.calculateMeanArterialPressure(systolic, diastolic)
            
            val bloodPressureData = BloodPressureManager.BloodPressureData(
                systolic = systolic,
                diastolic = diastolic,
                mean = mean,
                pulse = 72,
                comment = "Medição de teste"
            )
            
            // Insere os dados
            bloodPressureManager.insertBloodPressureData(bloodPressureData) { success, error ->
                runOnUiThread {
                    if (success) {
                        Toast.makeText(
                            this@BloodPressureActivity,
                            "Dados de pressão arterial salvos!",
                            Toast.LENGTH_SHORT
                        ).show()
                        
                        // Publica via MQTT
                        healthPublisher.publishBloodPressureData(bloodPressureData)
                        healthPublisher.publishBloodPressureAlert(bloodPressureData)
                        
                        // Lê os dados mais recentes
                        readLatestData()
                        
                    } else {
                        Toast.makeText(
                            this@BloodPressureActivity,
                            "Erro: $error",
                            Toast.LENGTH_LONG
                        ).show()
                    }
                }
            }
        }
    }
    
    private fun readLatestData() {
        bloodPressureManager.getLatestBloodPressureData { success, data, error ->
            runOnUiThread {
                if (success && data != null) {
                    val interpretation = bloodPressureManager.interpretBloodPressure(
                        data.systolic, data.diastolic
                    )
                    
                    Toast.makeText(
                        this,
                        "Pressão: ${data.systolic.toInt()}/${data.diastolic.toInt()} - $interpretation",
                        Toast.LENGTH_LONG
                    ).show()
                } else {
                    Toast.makeText(
                        this,
                        "Erro ao ler dados: $error",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            }
        }
    }
    
    override fun onDestroy() {
        super.onDestroy()
        bloodPressureManager.disconnect()
    }
} 