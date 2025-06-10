package com.example.mqttwearable.health

import android.content.Context
import android.util.Log
import androidx.health.services.client.HealthServices
import androidx.health.services.client.MeasureCallback
import androidx.health.services.client.MeasureClient
import androidx.health.services.client.PassiveListenerCallback
import androidx.health.services.client.PassiveMonitoringClient
import androidx.health.services.client.data.Availability
import androidx.health.services.client.data.DataPointContainer
import androidx.health.services.client.data.DataType
import androidx.health.services.client.data.DataTypeAvailability
import androidx.health.services.client.data.DeltaDataType
import androidx.health.services.client.data.PassiveListenerConfig
import androidx.health.services.client.getCapabilities
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import com.example.mqttwearable.mqtt.MqttHandler
import java.util.concurrent.CopyOnWriteArrayList
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

public class HealthPublisher(
    context: Context,
    private val mqttHandler: MqttHandler
) {
    private val passiveMonitoringClient: PassiveMonitoringClient =
        HealthServices.getClient(context).passiveMonitoringClient

    private val measureClient: MeasureClient =
        HealthServices.getClient(context).measureClient

    // Buffer para armazenar o último valor de cada tipo de dado
    private val latestData = mutableMapOf<String, Any>()
    private var senderJob: Job? = null
    // Timestamp da última atualização do listener
    private var lastUpdateTimestamp: Long? = null

    // Intervalo de envio em milissegundos
    var sendIntervalMs: Long = 5000L

    // Callback que recebe os lotes de dados enquanto o app está rodando em foreground
    private val passiveListener = object : PassiveListenerCallback {
        override fun onNewDataPointsReceived(dataPoints: DataPointContainer) {
            var updated = false
            dataPoints.getData(DataType.HEART_RATE_BPM)
                .lastOrNull()?.let {
                    if (it.value != 0.0) latestData["heartRateBpm"] = it.value
                    updated = true
                }

            dataPoints.getData(DataType.STEPS_DAILY)
                .lastOrNull()?.let { latestData["dailySteps"] = it.value; updated = true }

            dataPoints.getData(DataType.CALORIES_DAILY)
                .lastOrNull()?.let { latestData["dailyCalories"] = it.value; updated = true }

            dataPoints.getData(DataType.DISTANCE_DAILY)
                .lastOrNull()?.let { latestData["dailyDistance"] = it.value; updated = true }

            dataPoints.getData(DataType.FLOORS_DAILY)
                .lastOrNull()?.let { latestData["dailyFloors"] = it.value; updated = true }

            dataPoints.getData(DataType.ELEVATION_GAIN_DAILY)
                .lastOrNull()?.let { latestData["dailyElevationGain"] = it.value; updated = true }

            if (updated) {
                lastUpdateTimestamp = System.currentTimeMillis()
            }
        }
    }

    private fun mapToJson(map: Map<String, Any>): String {
        return map.entries.joinToString(prefix = "{", postfix = "}") { (k, v) ->
            val valueStr = if (v is Number) v.toString() else "\"$v\""
            "\"$k\":$valueStr"
        }
    }

    /** Registra o listener para os tipos de dados desejados. */
    suspend fun startPassiveMeasure() {
        val types = setOf(
            DataType.CALORIES_DAILY,      // calorias diárias
            DataType.DISTANCE_DAILY,      // distância diária (m)
            DataType.ELEVATION_GAIN_DAILY, // ganho de elevação diário
            DataType.FLOORS_DAILY,        // andares diários
            DataType.STEPS_DAILY,         // passos diários
            DataType.HEART_RATE_BPM       // batimentos (não tem diário, é amostragem)
        )
        val config = PassiveListenerConfig.builder()
            .setDataTypes(types)
            .build()
        passiveMonitoringClient.setPassiveListenerCallback(config, passiveListener)
        Log.d("HealthPublisher", "PassiveListener registered for $types")

        val capabilities = passiveMonitoringClient.getCapabilities().supportedDataTypesPassiveMonitoring
        Log.d("HealthPublisher", "Supported passive types: ${capabilities}")
        mqttHandler.publish("teste",  "Supported passive types: ${capabilities}")

        // Inicia o job de envio periódico
        if (senderJob == null) {
            senderJob = CoroutineScope(Dispatchers.IO).launch {
                while (true) {
                    delay(sendIntervalMs)
                    if (latestData.isNotEmpty()) {
                        val toSend = latestData.toMap().toMutableMap()
                        lastUpdateTimestamp?.let {
                            toSend["lastUpdateTime"] = formatIsoUtc(it)
                        }
                        val json = mapToJson(toSend)
                        Log.d("HealthPublisher", "Sending latest via MQTT: $json")
                        mqttHandler.publish("health/data", json)
                    }
                }
            }
        }
    }

    /** Cancela o listener */
    fun stopPassiveMeasure() {
        passiveMonitoringClient.clearPassiveListenerCallbackAsync()
        Log.d("HealthPublisher", "PassiveListener unregistered")
        senderJob?.cancel()
        senderJob = null
    }

    /**
     * Publica dados de pressão arterial via MQTT
     * @param bloodPressureData Dados de pressão arterial do Samsung Health SDK
     */
    fun publishBloodPressureData(bloodPressureData: BloodPressureManager.BloodPressureData) {
        val context = passiveMonitoringClient as Context
        val data = mutableMapOf<String, Any>().apply {
            put("systolic", bloodPressureData.systolic)
            put("diastolic", bloodPressureData.diastolic)
            put("meanArterialPressure", bloodPressureData.mean)
            put("measurementTime", formatIsoUtc(bloodPressureData.timestamp))
            put("deviceType", "Samsung Watch")
            put("dataSource", "Samsung Health SDK")
            
            // Campos opcionais
            bloodPressureData.pulse?.let { put("pulse", it) }
            bloodPressureData.comment?.let { put("comment", it) }
            
            // Interpretação médica
            val interpretation = when {
                bloodPressureData.systolic < 120 && bloodPressureData.diastolic < 80 -> "Normal"
                bloodPressureData.systolic < 130 && bloodPressureData.diastolic < 80 -> "Elevada"
                bloodPressureData.systolic < 140 || bloodPressureData.diastolic < 90 -> "Hipertensão Estágio 1"
                bloodPressureData.systolic < 180 || bloodPressureData.diastolic < 120 -> "Hipertensão Estágio 2"
                else -> "Crise Hipertensiva - Procure atendimento médico imediato"
            }
            put("interpretation", interpretation)
            
            // Categoria de risco
            val riskLevel = when {
                interpretation.contains("Normal") -> "LOW"
                interpretation.contains("Elevada") -> "MEDIUM"
                interpretation.contains("Hipertensão Estágio 1") -> "HIGH"
                interpretation.contains("Hipertensão Estágio 2") -> "VERY_HIGH"
                else -> "CRITICAL"
            }
            put("riskLevel", riskLevel)
        }
        
        val json = mapToJson(data)
        Log.d("HealthPublisher", "Publishing blood pressure data via MQTT: $json")
        
        // Publica no tópico específico de pressão arterial
        mqttHandler.publish("health/blood_pressure", json)
        
        // Também atualiza no tópico geral de dados de saúde
        latestData["lastBloodPressure"] = mapOf(
            "systolic" to bloodPressureData.systolic,
            "diastolic" to bloodPressureData.diastolic,
            "timestamp" to formatIsoUtc(bloodPressureData.timestamp),
            "interpretation" to when {
                bloodPressureData.systolic < 120 && bloodPressureData.diastolic < 80 -> "Normal"
                bloodPressureData.systolic < 130 && bloodPressureData.diastolic < 80 -> "Elevada"
                bloodPressureData.systolic < 140 || bloodPressureData.diastolic < 90 -> "Hipertensão Estágio 1"
                bloodPressureData.systolic < 180 || bloodPressureData.diastolic < 120 -> "Hipertensão Estágio 2"
                else -> "Crise Hipertensiva - Procure atendimento médico imediato"
            }
        )
    }

    /**
     * Publica alerta de pressão arterial crítica
     */
    fun publishBloodPressureAlert(bloodPressureData: BloodPressureManager.BloodPressureData) {
        val interpretation = when {
            bloodPressureData.systolic < 120 && bloodPressureData.diastolic < 80 -> "Normal"
            bloodPressureData.systolic < 130 && bloodPressureData.diastolic < 80 -> "Elevada"
            bloodPressureData.systolic < 140 || bloodPressureData.diastolic < 90 -> "Hipertensão Estágio 1"
            bloodPressureData.systolic < 180 || bloodPressureData.diastolic < 120 -> "Hipertensão Estágio 2"
            else -> "Crise Hipertensiva - Procure atendimento médico imediato"
        }
        
        if (interpretation.contains("Crise Hipertensiva")) {
            val alertData = mapOf(
                "alertType" to "BLOOD_PRESSURE_CRISIS",
                "severity" to "CRITICAL",
                "systolic" to bloodPressureData.systolic,
                "diastolic" to bloodPressureData.diastolic,
                "timestamp" to formatIsoUtc(bloodPressureData.timestamp),
                "message" to "Crise hipertensiva detectada - Procure atendimento médico imediato",
                "deviceId" to "samsung_watch",
                "recommendedAction" to "SEEK_IMMEDIATE_MEDICAL_ATTENTION"
            )
            
            val json = mapToJson(alertData)
            Log.w("HealthPublisher", "CRITICAL ALERT - Blood pressure crisis: $json")
            
            // Publica no tópico de alertas críticos
            mqttHandler.publish("health/alerts/critical", json)
        }
    }

    /**
     * Obtém os dados mais recentes incluindo pressão arterial
     */
    fun getLatestHealthData(): Map<String, Any> {
        val data = latestData.toMutableMap()
        lastUpdateTimestamp?.let {
            data["lastUpdateTime"] = formatIsoUtc(it)
        }
        return data
    }

    private fun listToJson(list: List<Map<String, Any>>): String {
        return "" // não será mais usado
    }

    private fun formatIsoUtc(timestamp: Long): String {
        val sdf = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
        sdf.timeZone = TimeZone.getTimeZone("UTC")
        return sdf.format(Date(timestamp))
    }
}
