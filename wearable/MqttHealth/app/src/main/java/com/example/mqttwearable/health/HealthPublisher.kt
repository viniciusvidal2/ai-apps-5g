package com.sae5g.mqttwearable.health

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
import com.sae5g.mqttwearable.mqtt.MqttHandler
import com.sae5g.mqttwearable.location.LocationManager
import com.sae5g.mqttwearable.data.SpO2DataManager
import com.sae5g.mqttwearable.data.DeviceIdManager
import com.sae5g.mqttwearable.connectivity.WiFiConnectivityManager
import java.util.concurrent.CopyOnWriteArrayList
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

public class HealthPublisher(
    private val context: Context,
    private val mqttHandler: MqttHandler
) : SpO2DataManager.SpO2DataListener {
    private val wifiConnectivityManager = WiFiConnectivityManager(context)
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
    
    // SpO2 atual
    private var currentSpO2: Int? = null

    // Intervalo de envio em milissegundos (1 minuto)
//    var sendIntervalMs: Long = 60000L
    var sendIntervalMs: Long = 10000L

    init {
        // Garantir que o DeviceIdManager está inicializado
        DeviceIdManager.initializeDeviceId(context)
    }

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
    
    // Implementação do SpO2DataListener
    override fun onSpO2ValueUpdated(spO2Value: Int, timestamp: Long) {
        currentSpO2 = spO2Value
        Log.d("HealthPublisher", "SpO2 recebido: $spO2Value%")
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
        
        // Registrar listener para SpO2
        SpO2DataManager.addListener(this)
        
        // Obter SpO2 atual se disponível
        currentSpO2 = SpO2DataManager.getCurrentSpO2()
        
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

        // Inicia o job de envio periódico
        if (senderJob == null) {
            senderJob = CoroutineScope(Dispatchers.IO).launch {
                // Aguardar 3 segundos para sincronizar com timer visual
                delay(3000)
                while (true) {
                    if (latestData.isNotEmpty()) {
                        val toSend = latestData.toMap().toMutableMap()
                        
                        // Adicionar hora atual do dispositivo
                        val sdf = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
                        sdf.timeZone = TimeZone.getTimeZone("UTC")
                        val currentTime = sdf.format(Date())
                        toSend["time"] = currentTime
                        
                        lastUpdateTimestamp?.let {
                            toSend["lastUpdateTime"] = formatIsoUtc(it)
                        }
                        
                        // Adicionar Device ID
                        toSend["id"] = DeviceIdManager.getDeviceId()
                        
                        // Adicionar localização se disponível
                        if (currentLatitude != null && currentLongitude != null) {
                            toSend["latitude"] = currentLatitude!!
                            toSend["longitude"] = currentLongitude!!
                        }
                        
                        // Adicionar SpO2 se disponível
                        currentSpO2?.let { spO2 ->
                            toSend["spo2"] = spO2
                        }
                        
                        val json = mapToJson(toSend)
                        Log.d("HealthPublisher", "Verificando WiFi antes de enviar dados via MQTT...")
                        
                        // Verificar WiFi antes de enviar
                        if (wifiConnectivityManager.isWiFiConnected()) {
                            val networkName = wifiConnectivityManager.getCurrentNetworkName()
                            Log.d("HealthPublisher", "WiFi OK (${networkName}), enviando dados: $json")
                            mqttHandler.publish("health/data", json) { success ->
                                if (success) {
                                    Log.d("HealthPublisher", "Dados enviados com sucesso via WiFi: $networkName")
                                } else {
                                    Log.w("HealthPublisher", "Falha ao enviar dados mesmo com WiFi conectado")
                                }
                            }
                        } else {
                            Log.w("HealthPublisher", "Sem WiFi - Dados não enviados: $json")
                        }
                    }
                    delay(sendIntervalMs)
                }
            }
        }
    }

    /** Cancela o listener */
    fun stopPassiveMeasure() {
        passiveMonitoringClient.clearPassiveListenerCallbackAsync()
        locationManager.stopLocationUpdates()
        SpO2DataManager.removeListener(this)
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
