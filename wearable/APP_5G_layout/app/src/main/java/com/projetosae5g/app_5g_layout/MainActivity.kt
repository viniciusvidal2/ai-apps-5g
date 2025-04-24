package com.projetosae5g.app_5g_layout

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.BatteryManager
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.view.WindowManager
import android.widget.Button
import android.widget.EditText
import android.widget.Switch
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.core.app.ActivityCompat
import androidx.health.services.client.HealthServices
import androidx.health.services.client.MeasureCallback
import androidx.health.services.client.MeasureClient
import androidx.health.services.client.data.Availability
import androidx.health.services.client.data.DataPointContainer
import androidx.health.services.client.data.DataType
import androidx.health.services.client.data.DeltaDataType
import androidx.lifecycle.lifecycleScope
import androidx.viewpager2.widget.ViewPager2
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {

    private lateinit var measureClient: MeasureClient
    private var exerciseMetrics = ExerciseMetrics()

    // Controles de tempo
    private lateinit var editTextInterval: EditText
    private lateinit var buttonIncrease: Button
    private lateinit var buttonDecrease: Button
    private lateinit var buttonMqttConfig: Button
    private lateinit var switchBackground: Switch
    private lateinit var switchKeepScreenOn: Switch
    private var measurementInterval: Long = 1 // segundos
    private var lastUpdateTime: Long = 0  // em milissegundos
    private var isServiceRunning = false
    private var keepScreenOn = false // flag para tela sempre ligada

    // ViewPager2 e adapter para métricas
    private lateinit var viewPagerMetrics: ViewPager2
    private lateinit var metricPagerAdapter: MetricPagerAdapter

    // MqttHandler
    private lateinit var mainApplication: MainApplication
    
    // Código de solicitação de permissão
    private val PERMISSIONS_REQUEST_CODE = 1001
    
    // BroadcastReceiver para monitorar o nível da bateria
    private val batteryReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            if (intent.action == Intent.ACTION_BATTERY_CHANGED) {
                val level = intent.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
                val scale = intent.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
                val batteryPct = level * 100 / scale
                exerciseMetrics = exerciseMetrics.copy(batteryLevel = batteryPct)
                updateMetricsDisplay()
            }
        }
    }

    // Atualiza a exibição das métricas
    private fun updateMetricsDisplay() {
        val metricsList = listOf(
            "BATIMENTOS CARDÍACOS: ${exerciseMetrics.heartRate ?: "--"} BPM",
            "NÍVEL DA BATERIA: ${exerciseMetrics.batteryLevel ?: "--"}%"
        )
        runOnUiThread {
            metricPagerAdapter.updateMetrics(metricsList)
        }
    }

    // Callback de medição
    private val heartRateCallback = object : MeasureCallback {
        override fun onDataReceived(data: DataPointContainer) {
            // Atualiza os dados de batimentos cardíacos
            exerciseMetrics = exerciseMetrics.update(data)
            val currentTime = System.currentTimeMillis()
            if (currentTime - lastUpdateTime >= measurementInterval * 1000) {
                lastUpdateTime = currentTime
                updateMetricsDisplay()
            }
        }

        override fun onAvailabilityChanged(
            dataType: DeltaDataType<*, *>,
            availability: Availability
        ) {
            Log.d("MainActivity", "onAvailabilityChanged: dataType=$dataType, availability=$availability")
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        checkPermissions()

        // Obter a referência da aplicação
        mainApplication = application as MainApplication

        // Inicializa controles de tempo
        editTextInterval = findViewById(R.id.editTextInterval)
        buttonIncrease = findViewById(R.id.buttonIncrease)
        buttonDecrease = findViewById(R.id.buttonDecrease)
        buttonMqttConfig = findViewById(R.id.buttonMqttConfig)
        switchBackground = findViewById(R.id.switchBackground)
        switchKeepScreenOn = findViewById(R.id.switchKeepScreenOn)
        
        // Carregar preferências salvas
        val sharedPreferences = getSharedPreferences("service_prefs", Context.MODE_PRIVATE)
        val savedInterval = sharedPreferences.getLong("measurement_interval", 1)
        val savedAutoStart = sharedPreferences.getBoolean("service_auto_start", false)
        val savedKeepScreenOn = sharedPreferences.getBoolean("keep_screen_on", false)
        
        // Aplicar preferências carregadas
        measurementInterval = savedInterval
        editTextInterval.setText(measurementInterval.toString())
        switchBackground.isChecked = savedAutoStart
        switchKeepScreenOn.isChecked = savedKeepScreenOn
        
        // Aplicar configuração de tela ligada se necessário
        keepScreenOn = savedKeepScreenOn
        if (keepScreenOn) {
            window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        } else {
            window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
        
        // Se o modo de inicialização automática estiver ativado, iniciar o serviço
        if (savedAutoStart && !isServiceRunning && mainApplication.mqttHandler.isConnected()) {
            startBackgroundService()
        }

        buttonIncrease.setOnClickListener {
            measurementInterval++
            editTextInterval.setText(measurementInterval.toString())
            savePreferences()
        }
        
        buttonDecrease.setOnClickListener {
            if (measurementInterval > 1) {
                measurementInterval--
                editTextInterval.setText(measurementInterval.toString())
                savePreferences()
            }
        }
        
        editTextInterval.setOnFocusChangeListener { _, hasFocus ->
            if (!hasFocus) {
                val newInterval = editTextInterval.text.toString().toLongOrNull()
                if (newInterval != null && newInterval >= 1) {
                    measurementInterval = newInterval
                    savePreferences()
                } else {
                    editTextInterval.setText(measurementInterval.toString())
                }
            }
        }
        
        // Configura botão MQTT
        buttonMqttConfig.setOnClickListener {
            val intent = Intent(this, MqttConfigActivity::class.java)
            startActivity(intent)
        }
        
        // Configura switch de serviço em segundo plano
        switchBackground.setOnCheckedChangeListener { _, isChecked ->
            if (isChecked) {
                if (hasRequiredPermissions()) {
                    startBackgroundService()
                } else {
                    // Se não tem permissões, solicitar e reverter o switch
                    switchBackground.isChecked = false
                    requestRequiredPermissions()
                    Toast.makeText(this, "É necessário conceder as permissões primeiro", Toast.LENGTH_LONG).show()
                }
            } else {
                stopBackgroundService()
            }
            savePreferences()
        }

        // Configura switch para manter a tela ligada
        switchKeepScreenOn.setOnCheckedChangeListener { _, isChecked ->
            keepScreenOn = isChecked
            if (isChecked) {
                // Manter a tela sempre ligada
                window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
                Toast.makeText(this, "Tela sempre ligada ativada", Toast.LENGTH_SHORT).show()
            } else {
                // Permitir que a tela apague normalmente
                window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
                Toast.makeText(this, "Tela sempre ligada desativada", Toast.LENGTH_SHORT).show()
            }
            savePreferences()
        }

        // Inicializa ViewPager2 e adapter com valores iniciais
        viewPagerMetrics = findViewById(R.id.viewPagerMetrics)
        metricPagerAdapter = MetricPagerAdapter(
            listOf(
                "BATIMENTOS CARDÍACOS: --",
                "NÍVEL DA BATERIA: --%"
            )
        )
        viewPagerMetrics.adapter = metricPagerAdapter
        viewPagerMetrics.orientation = ViewPager2.ORIENTATION_VERTICAL

        // Inicializa o MeasureClient
        measureClient = HealthServices.getClient(this).measureClient

        lifecycleScope.launch {
            val capabilities = withContext(Dispatchers.IO) {
                measureClient.getCapabilitiesAsync().get()
            }
            val isHeartRateAvailable = DataType.HEART_RATE_BPM in capabilities.supportedDataTypesMeasure
            if (isHeartRateAvailable) {
                lifecycleScope.launch {
                    measureClient.registerMeasureCallback(DataType.HEART_RATE_BPM, heartRateCallback)
                }
            }
        }

        // Registra o receptor de bateria
        registerReceiver(batteryReceiver, IntentFilter(Intent.ACTION_BATTERY_CHANGED))
    }
    
    // Verificar se todas as permissões necessárias foram concedidas
    private fun hasRequiredPermissions(): Boolean {
        // Verificar a permissão de FOREGROUND_SERVICE_HEALTH (obrigatória)
        val hasForegroundServiceHealth = ActivityCompat.checkSelfPermission(
            this, 
            Manifest.permission.FOREGROUND_SERVICE_HEALTH
        ) == PackageManager.PERMISSION_GRANTED
        
        // Verificar pelo menos uma das permissões opcionais
        val hasActivityRecognition = ActivityCompat.checkSelfPermission(
            this,
            Manifest.permission.ACTIVITY_RECOGNITION
        ) == PackageManager.PERMISSION_GRANTED
        
        val hasBodySensors = ActivityCompat.checkSelfPermission(
            this,
            Manifest.permission.BODY_SENSORS
        ) == PackageManager.PERMISSION_GRANTED
        
        val hasHighSamplingRateSensors = ActivityCompat.checkSelfPermission(
            this,
            Manifest.permission.HIGH_SAMPLING_RATE_SENSORS
        ) == PackageManager.PERMISSION_GRANTED
        
        // Precisa da permissão obrigatória E pelo menos uma das opcionais
        return hasForegroundServiceHealth && (hasActivityRecognition || hasBodySensors || hasHighSamplingRateSensors)
    }
    
    // Salvar preferências para inicialização automática
    private fun savePreferences() {
        val sharedPreferences = getSharedPreferences("service_prefs", Context.MODE_PRIVATE)
        sharedPreferences.edit().apply {
            putLong("measurement_interval", measurementInterval)
            putBoolean("service_auto_start", switchBackground.isChecked)
            putBoolean("keep_screen_on", keepScreenOn)
            apply()
        }
    }
    
    // Método para iniciar o serviço em segundo plano
    private fun startBackgroundService() {
        if (!isServiceRunning) {
            if (mainApplication.mqttHandler.isConnected()) {
                // Verificar se todas as permissões necessárias foram concedidas
                if (hasRequiredPermissions()) {
                    Log.d("MainActivity", "Iniciando serviço em segundo plano...")
                    
                    val serviceIntent = Intent(this, MonitorService::class.java).apply {
                        putExtra("interval", measurementInterval)
                    }
                    
                    try {
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                            startForegroundService(serviceIntent)
                        } else {
                            startService(serviceIntent)
                        }
                        
                        isServiceRunning = true
                        Toast.makeText(this, "Serviço em segundo plano iniciado", Toast.LENGTH_SHORT).show()
                    } catch (e: Exception) {
                        Log.e("MainActivity", "Erro ao iniciar serviço", e)
                        Toast.makeText(this, "Erro ao iniciar serviço: ${e.message}", Toast.LENGTH_LONG).show()
                        switchBackground.isChecked = false
                        savePreferences()
                    }
                } else {
                    switchBackground.isChecked = false
                    savePreferences()
                    requestRequiredPermissions()
                    Toast.makeText(this, "É necessário conceder as permissões para executar em segundo plano", Toast.LENGTH_LONG).show()
                }
            } else {
                switchBackground.isChecked = false
                savePreferences()
                Toast.makeText(this, "Conecte ao servidor MQTT primeiro", Toast.LENGTH_LONG).show()
            }
        }
    }
    
    // Método para parar o serviço em segundo plano
    private fun stopBackgroundService() {
        if (isServiceRunning) {
            Log.d("MainActivity", "Parando serviço em segundo plano...")
            stopService(Intent(this, MonitorService::class.java))
            isServiceRunning = false
            Toast.makeText(this, "Serviço em segundo plano parado", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onResume() {
        super.onResume()
        // Aplicar configuração de tela ligada, caso tenha mudado
        if (keepScreenOn) {
            window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        } else {
            window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
        
        // Verificar status do MQTT e atualizar a UI se necessário
        if (mainApplication.mqttHandler.isConnected()) {
            // Se estiver conectado, iniciar a publicação de medições
            startMqttPublishing()
        }
    }

    override fun onPause() {
        super.onPause()
    }

    override fun onDestroy() {
        super.onDestroy()
        // Desregistra o receptor de bateria quando a atividade é destruída
        unregisterReceiver(batteryReceiver)
    }
    
    // Iniciar a publicação periódica de dados MQTT
    private fun startMqttPublishing() {
        // Fornecer funções que retornam os dados mais recentes
        mainApplication.startMqttPublishing(
            heartRateProvider = { exerciseMetrics.heartRate },
            batteryLevelProvider = { exerciseMetrics.batteryLevel },
            secondsMeasureProvider = { measurementInterval }
        )
    }
    
    // Solicitar todas as permissões necessárias
    private fun requestRequiredPermissions() {
        val requiredPermissions = mutableListOf<String>()
        
        // Verificar e adicionar as permissões necessárias
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.FOREGROUND_SERVICE_HEALTH) != 
            PackageManager.PERMISSION_GRANTED) {
            requiredPermissions.add(Manifest.permission.FOREGROUND_SERVICE_HEALTH)
        }
        
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.BODY_SENSORS) != 
            PackageManager.PERMISSION_GRANTED) {
            requiredPermissions.add(Manifest.permission.BODY_SENSORS)
        }
        
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.ACTIVITY_RECOGNITION) != 
            PackageManager.PERMISSION_GRANTED) {
            requiredPermissions.add(Manifest.permission.ACTIVITY_RECOGNITION)
        }
        
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.HIGH_SAMPLING_RATE_SENSORS) != 
            PackageManager.PERMISSION_GRANTED) {
            requiredPermissions.add(Manifest.permission.HIGH_SAMPLING_RATE_SENSORS)
        }
        
        // Permissões para Wi-Fi
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) != 
            PackageManager.PERMISSION_GRANTED) {
            requiredPermissions.add(Manifest.permission.ACCESS_FINE_LOCATION)
        }
        
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.CHANGE_WIFI_STATE) != 
            PackageManager.PERMISSION_GRANTED) {
            requiredPermissions.add(Manifest.permission.CHANGE_WIFI_STATE)
        }
        
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.CHANGE_NETWORK_STATE) != 
            PackageManager.PERMISSION_GRANTED) {
            requiredPermissions.add(Manifest.permission.CHANGE_NETWORK_STATE)
        }
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q && 
            ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_BACKGROUND_LOCATION) != 
            PackageManager.PERMISSION_GRANTED) {
            requiredPermissions.add(Manifest.permission.ACCESS_BACKGROUND_LOCATION)
        }
        
        if (requiredPermissions.isNotEmpty()) {
            ActivityCompat.requestPermissions(
                this, 
                requiredPermissions.toTypedArray(),
                PERMISSIONS_REQUEST_CODE
            )
        }
    }

    // Gerenciar o resultado da solicitação de permissões
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        
        if (requestCode == PERMISSIONS_REQUEST_CODE) {
            if (grantResults.isNotEmpty() && grantResults.all { it == PackageManager.PERMISSION_GRANTED }) {
                // Todas as permissões foram concedidas
                if (switchBackground.isChecked) {
                    startBackgroundService()
                }
            } else {
                // Alguma permissão foi negada
                Toast.makeText(
                    this,
                    "As permissões são necessárias para executar o serviço em segundo plano",
                    Toast.LENGTH_LONG
                ).show()
                
                // Desmarcar o switch se estiver marcado
                switchBackground.isChecked = false
                savePreferences()
            }
        }
    }
    
    private fun checkPermissions() {
        requestRequiredPermissions()
    }
}