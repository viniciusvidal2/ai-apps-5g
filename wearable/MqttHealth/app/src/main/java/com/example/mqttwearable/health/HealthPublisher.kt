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
import com.example.mqttwearable.location.LocationManager
import java.util.concurrent.CopyOnWriteArrayList
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

public class HealthPublisher(
    private val context: Context,
    private val mqttHandler: MqttHandler
) {
    private val passiveMonitoringClient: PassiveMonitoringClient =
        HealthServices.getClient(context).passiveMonitoringClient

    private val measureClient: MeasureClient =
        HealthServices.getClient(context).measureClient

    // LocationManager para obter GPS
    private val locationManager = LocationManager(context)
    
    // Buffer para armazenar o último valor de cada tipo de dado
    private val latestData = mutableMapOf<String, Any>()
    private var senderJob: Job? = null
    // Timestamp da última atualização do listener
    private var lastUpdateTimestamp: Long? = null
    
    // Localização atual
    private var currentLatitude: Double? = null
    private var currentLongitude: Double? = null

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
        // Configurar listener de localização
        locationManager.setLocationUpdateListener(object : LocationManager.LocationUpdateListener {
            override fun onLocationUpdate(latitude: Double, longitude: Double) {
                currentLatitude = latitude
                currentLongitude = longitude
                Log.d("HealthPublisher", "Localização atualizada: $latitude, $longitude")
            }
            
            override fun onLocationError(error: String) {
                Log.e("HealthPublisher", "Erro de localização: $error")
            }
        })
        
        // Iniciar atualizações de localização
        locationManager.startLocationUpdates()
        
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
                        
                        // Adicionar localização se disponível
                        if (currentLatitude != null && currentLongitude != null) {
                            toSend["latitude"] = currentLatitude!!
                            toSend["longitude"] = currentLongitude!!
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
        locationManager.stopLocationUpdates()
        Log.d("HealthPublisher", "PassiveListener unregistered")
        senderJob?.cancel()
        senderJob = null
    }

    private fun listToJson(list: List<Map<String, Any>>): String {
        return "" // não será mais usado
    }

    private fun formatIsoUtc(timestamp: Long): String {
        val sdf = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
        sdf.timeZone = TimeZone.getTimeZone("UTC")
        return sdf.format(Date(timestamp))
    }
    
    /** Obter localização atual */
    fun getCurrentLocation(): Pair<Double, Double>? {
        return if (currentLatitude != null && currentLongitude != null) {
            Pair(currentLatitude!!, currentLongitude!!)
        } else {
            locationManager.getCurrentLocation()
        }
    }
}
