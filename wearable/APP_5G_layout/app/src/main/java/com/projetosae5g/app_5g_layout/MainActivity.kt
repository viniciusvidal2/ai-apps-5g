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
import android.widget.Button
import android.widget.EditText
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
    private var measurementInterval: Long = 1 // segundos
    private var lastUpdateTime: Long = 0  // em milissegundos

    // ViewPager2 e adapter para métricas
    private lateinit var viewPagerMetrics: ViewPager2
    private lateinit var metricPagerAdapter: MetricPagerAdapter

    // MqttHandler
    private lateinit var mainApplication: MainApplication
    
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

        buttonIncrease.setOnClickListener {
            measurementInterval++
            editTextInterval.setText(measurementInterval.toString())
        }
        
        buttonDecrease.setOnClickListener {
            if (measurementInterval > 1) {
                measurementInterval--
                editTextInterval.setText(measurementInterval.toString())
            }
        }
        
        editTextInterval.setOnFocusChangeListener { _, hasFocus ->
            if (!hasFocus) {
                val newInterval = editTextInterval.text.toString().toLongOrNull()
                if (newInterval != null && newInterval >= 1) {
                    measurementInterval = newInterval
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
        
        // Não iniciar a publicação MQTT automaticamente para evitar falhas
        // Isso será iniciado após o usuário configurar e conectar o MQTT
    }

    override fun onResume() {
        super.onResume()
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

    private fun checkPermissions() {
        val permissionsNeeded = mutableListOf<String>()
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.BODY_SENSORS) != PackageManager.PERMISSION_GRANTED) {
            permissionsNeeded.add(Manifest.permission.BODY_SENSORS)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            if (ActivityCompat.checkSelfPermission(this, Manifest.permission.ACTIVITY_RECOGNITION) != PackageManager.PERMISSION_GRANTED) {
                permissionsNeeded.add(Manifest.permission.ACTIVITY_RECOGNITION)
            }
        }
        if (permissionsNeeded.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, permissionsNeeded.toTypedArray(), 1001)
        }
    }
}
