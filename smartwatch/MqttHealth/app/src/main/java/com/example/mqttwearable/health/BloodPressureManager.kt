package com.example.mqttwearable.health

import android.content.Context
import android.util.Log
import com.samsung.android.sdk.healthdata.*
import java.util.*

/**
 * Gerenciador para dados de pressão arterial usando Samsung Health SDK
 * Baseado na documentação: https://developer.samsung.com/health/android/data/api-reference/com/samsung/android/sdk/healthdata/HealthConstants.BloodPressure.html
 */
class BloodPressureManager(private val context: Context) {
    
    private var healthDataStore: HealthDataStore? = null
    private val tag = "BloodPressureManager"
    
    // Callback para conexão com Samsung Health
    private val connectionListener = object : HealthDataStore.ConnectionListener {
        override fun onConnected() {
            Log.d(tag, "Samsung Health conectado com sucesso")
            requestPermissions()
        }
        
        override fun onConnectionFailed(error: HealthConnectionErrorResult) {
            Log.e(tag, "Falha na conexão com Samsung Health: ${error.errorCode}")
        }
        
        override fun onDisconnected() {
            Log.d(tag, "Samsung Health desconectado")
        }
    }
    
    /**
     * Inicializa a conexão com o Samsung Health
     */
    fun initialize() {
        healthDataStore = HealthDataStore(context, connectionListener)
        healthDataStore?.connectService()
    }
    
    /**
     * Solicita permissões para leitura e escrita de dados de pressão arterial
     */
    private fun requestPermissions() {
        val permissionManager = HealthPermissionManager(healthDataStore!!)
        
        // Configura as permissões necessárias para pressão arterial
        val permissionKeys = setOf(
            HealthPermissionManager.PermissionKey(
                HealthConstants.BloodPressure.HEALTH_DATA_TYPE,
                HealthPermissionManager.PermissionType.READ
            ),
            HealthPermissionManager.PermissionKey(
                HealthConstants.BloodPressure.HEALTH_DATA_TYPE,
                HealthPermissionManager.PermissionType.WRITE
            )
        )
        
        try {
            permissionManager.requestPermissions(permissionKeys)
                .setResultListener { result ->
                    val resultMap = result.resultMap
                    if (resultMap.values.contains(false)) {
                        Log.e(tag, "Nem todas as permissões foram concedidas")
                    } else {
                        Log.d(tag, "Todas as permissões concedidas com sucesso")
                    }
                }
        } catch (e: Exception) {
            Log.e(tag, "Erro ao solicitar permissões: ${e.message}")
        }
    }
    
    /**
     * Dados de pressão arterial
     */
    data class BloodPressureData(
        val systolic: Float,      // Pressão sistólica (máxima)
        val diastolic: Float,     // Pressão diastólica (mínima)
        val mean: Float,          // Pressão média
        val pulse: Int? = null,   // Pulso (opcional)
        val comment: String? = null, // Comentário (opcional)
        val timestamp: Long = System.currentTimeMillis()
    )
    
    /**
     * Insere dados de pressão arterial no Samsung Health
     */
    fun insertBloodPressureData(
        data: BloodPressureData,
        callback: (Boolean, String?) -> Unit
    ) {
        val healthDataResolver = HealthDataResolver(healthDataStore!!, null)
        
        // Obtém o dispositivo local
        val deviceManager = HealthDeviceManager(healthDataStore!!)
        val localDevice = deviceManager.localDevice
        
        // Cria o objeto de dados conforme a documentação da Samsung
        val healthData = HealthData().apply {
            setSourceDevice(localDevice.uuid) // Define o dispositivo de origem
            putFloat(HealthConstants.BloodPressure.SYSTOLIC, data.systolic)
            putFloat(HealthConstants.BloodPressure.DIASTOLIC, data.diastolic)
            putFloat(HealthConstants.BloodPressure.MEAN, data.mean)
            putLong(HealthConstants.BloodPressure.START_TIME, data.timestamp)
            putLong(HealthConstants.BloodPressure.TIME_OFFSET, TimeZone.getDefault().rawOffset.toLong())
            
            // Campos opcionais
            data.pulse?.let { putInt(HealthConstants.BloodPressure.PULSE, it) }
            data.comment?.let { putString(HealthConstants.BloodPressure.COMMENT, it) }
        }
        
                val insertRequest = HealthDataResolver.InsertRequest.Builder()
            .setDataType(HealthConstants.BloodPressure.HEALTH_DATA_TYPE)
            .build()

        // Adiciona o objeto HealthData ao request após o build()
        insertRequest.addHealthData(healthData)

        try {
            healthDataResolver.insert(insertRequest)
                .setResultListener { result ->
                    if (result.status == HealthResultHolder.BaseResult.STATUS_SUCCESSFUL) {
                        Log.d(tag, "Dados de pressão arterial inseridos com sucesso")
                        callback(true, null)
                    } else {
                        val error = "Erro ao inserir dados: ${result.status}"
                        Log.e(tag, error)
                        callback(false, error)
                    }
                }
        } catch (e: Exception) {
            val error = "Exceção ao inserir dados: ${e.message}"
            Log.e(tag, error)
            callback(false, error)
        }
    }
    
    /**
     * Lê dados de pressão arterial do Samsung Health
     */
    fun readBloodPressureData(
        startTime: Long,
        endTime: Long,
        callback: (Boolean, List<BloodPressureData>?, String?) -> Unit
    ) {
        val healthDataResolver = HealthDataResolver(healthDataStore!!, null)
        
        // Cria filtro para o período especificado
        val filter = HealthDataResolver.Filter.and(
            HealthDataResolver.Filter.greaterThanEquals(
                HealthConstants.BloodPressure.START_TIME,
                startTime
            ),
            HealthDataResolver.Filter.lessThanEquals(
                HealthConstants.BloodPressure.START_TIME,
                endTime
            )
        )
        
        val readRequest = HealthDataResolver.ReadRequest.Builder()
            .setDataType(HealthConstants.BloodPressure.HEALTH_DATA_TYPE)
            .setProperties(
                arrayOf(
                    HealthConstants.BloodPressure.SYSTOLIC,
                    HealthConstants.BloodPressure.DIASTOLIC,
                    HealthConstants.BloodPressure.MEAN,
                    HealthConstants.BloodPressure.PULSE,
                    HealthConstants.BloodPressure.COMMENT,
                    HealthConstants.BloodPressure.START_TIME
                )
            )
            .setFilter(filter)
            .build()
        
        try {
            healthDataResolver.read(readRequest)
                .setResultListener { result ->
                    if (result.status == HealthResultHolder.BaseResult.STATUS_SUCCESSFUL) {
                        val bloodPressureList = mutableListOf<BloodPressureData>()
                        
                        try {
                            for (data in result.iterator()) {
                                val systolic = data.getFloat(HealthConstants.BloodPressure.SYSTOLIC)
                                val diastolic = data.getFloat(HealthConstants.BloodPressure.DIASTOLIC)
                                val mean = data.getFloat(HealthConstants.BloodPressure.MEAN)
                                val pulse = try {
                                    data.getInt(HealthConstants.BloodPressure.PULSE)
                                } catch (e: Exception) { null }
                                val comment = try {
                                    data.getString(HealthConstants.BloodPressure.COMMENT)
                                } catch (e: Exception) { null }
                                val timestamp = data.getLong(HealthConstants.BloodPressure.START_TIME)
                                
                                bloodPressureList.add(
                                    BloodPressureData(
                                        systolic = systolic,
                                        diastolic = diastolic,
                                        mean = mean,
                                        pulse = pulse,
                                        comment = comment,
                                        timestamp = timestamp
                                    )
                                )
                            }
                            
                            Log.d(tag, "Lidos ${bloodPressureList.size} registros de pressão arterial")
                            callback(true, bloodPressureList, null)
                            
                        } catch (e: Exception) {
                            val error = "Erro ao processar dados lidos: ${e.message}"
                            Log.e(tag, error)
                            callback(false, null, error)
                        }
                    } else {
                        val error = "Erro ao ler dados: ${result.status}"
                        Log.e(tag, error)
                        callback(false, null, error)
                    }
                }
        } catch (e: Exception) {
            val error = "Exceção ao ler dados: ${e.message}"
            Log.e(tag, error)
            callback(false, null, error)
        }
    }
    
    /**
     * Obtém dados de pressão arterial mais recentes
     */
    fun getLatestBloodPressureData(callback: (Boolean, BloodPressureData?, String?) -> Unit) {
        val endTime = System.currentTimeMillis()
        val startTime = endTime - (7 * 24 * 60 * 60 * 1000L) // Últimos 7 dias
        
        readBloodPressureData(startTime, endTime) { success, dataList, error ->
            if (success && !dataList.isNullOrEmpty()) {
                // Retorna o mais recente (último da lista)
                val latest = dataList.maxByOrNull { it.timestamp }
                callback(true, latest, null)
            } else {
                callback(false, null, error ?: "Nenhum dado encontrado")
            }
        }
    }
    

    
    /**
     * Desconecta do Samsung Health
     */
    fun disconnect() {
        healthDataStore?.disconnectService()
    }
    
    /**
     * Verifica se a conexão com Samsung Health está ativa
     */
    fun isConnected(): Boolean {
        return healthDataStore != null
    }
    
    /**
     * Calcula a pressão arterial média (MAP - Mean Arterial Pressure)
     * Fórmula: MAP = (2 × diastólica + sistólica) / 3
     */
    fun calculateMeanArterialPressure(systolic: Float, diastolic: Float): Float {
        return (2 * diastolic + systolic) / 3
    }
    
    /**
     * Interpreta os valores de pressão arterial
     */
    fun interpretBloodPressure(systolic: Float, diastolic: Float): String {
        return when {
            systolic < 120 && diastolic < 80 -> "Normal"
            systolic < 130 && diastolic < 80 -> "Elevada"
            systolic < 140 || diastolic < 90 -> "Hipertensão Estágio 1"
            systolic < 180 || diastolic < 120 -> "Hipertensão Estágio 2"
            else -> "Crise Hipertensiva - Procure atendimento médico imediato"
        }
    }
} 