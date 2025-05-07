package com.projetosae5g.app_5g_layout

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
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
import com.google.android.gms.maps.CameraUpdateFactory
import com.google.android.gms.maps.GoogleMap
import com.google.android.gms.maps.MapView
import com.google.android.gms.maps.OnMapReadyCallback
import com.google.android.gms.maps.model.LatLng
import com.google.android.gms.maps.model.MarkerOptions
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import androidx.appcompat.app.AlertDialog
import androidx.viewpager2.widget.ViewPager2

class MainActivity : ComponentActivity(), OnMapReadyCallback, LocationListener {
    private val TAG = "MainActivity"

    private lateinit var measureClient: MeasureClient
    private var exerciseMetrics = ExerciseMetrics()
    private lateinit var viewPager: ViewPager2
    private val stepCounterService by lazy { StepCounterService(this) }

    // Controles de tempo
    private lateinit var editTextInterval: EditText
    private lateinit var buttonIncrease: Button
    private lateinit var buttonDecrease: Button
    private lateinit var buttonMqttConfig: Button
    private lateinit var switchBackground: Switch
    private lateinit var switchKeepScreenOn: Switch
    private lateinit var buttonViewMetrics: Button
    private var measurementInterval: Long = 1 // segundos
    private var lastUpdateTime: Long = 0  // em milissegundos
    private var isServiceRunning = false
    private var keepScreenOn = false // flag para tela sempre ligada

    // Mapa e localização
    private lateinit var mapView: MapView
    private lateinit var googleMap: GoogleMap
    private lateinit var locationManager: LocationManager
    private var lastLocation: Location? = null
    private val MIN_DISTANCE_CHANGE_FOR_UPDATES: Float = 5f // 5 metros
    private val MIN_TIME_BW_UPDATES: Long = 10000 // 10 segundos

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
        // Atualizar apenas o LiveData para a MetricsActivity
        runOnUiThread {
            MetricsActivity.metricsLiveData.postValue(exerciseMetrics)
        }
    }

    // Callback de medição
    private val heartRateCallback = object : MeasureCallback {
        override fun onAvailabilityChanged(dataType: DeltaDataType<*, *>, availability: Availability) {
            Log.d(TAG, "Disponibilidade do sensor de frequência cardíaca alterada: $availability")
        }

        override fun onDataReceived(data: DataPointContainer) {
            exerciseMetrics = exerciseMetrics.update(data)
            val currentTime = System.currentTimeMillis()
            if (currentTime - lastUpdateTime >= measurementInterval * 1000) {
                lastUpdateTime = currentTime
                updateMetricsDisplay()
            }
        }
    }

    private val stepsCallback = object : MeasureCallback {
        override fun onAvailabilityChanged(dataType: DeltaDataType<*, *>, availability: Availability) {
            Log.d(TAG, "Disponibilidade do sensor de passos alterada: $availability")
        }

        override fun onDataReceived(data: DataPointContainer) {
            exerciseMetrics = exerciseMetrics.update(data)
            val currentTime = System.currentTimeMillis()
            if (currentTime - lastUpdateTime >= measurementInterval * 1000) {
                lastUpdateTime = currentTime
                updateMetricsDisplay()
            }
        }
    }

    private val distanceCallback = object : MeasureCallback {
        override fun onAvailabilityChanged(dataType: DeltaDataType<*, *>, availability: Availability) {
            Log.d(TAG, "Disponibilidade do sensor de distância alterada: $availability")
        }

        override fun onDataReceived(data: DataPointContainer) {
            exerciseMetrics = exerciseMetrics.update(data)
            val currentTime = System.currentTimeMillis()
            if (currentTime - lastUpdateTime >= measurementInterval * 1000) {
                lastUpdateTime = currentTime
                updateMetricsDisplay()
            }
        }
    }

    private val caloriesCallback = object : MeasureCallback {
        override fun onAvailabilityChanged(dataType: DeltaDataType<*, *>, availability: Availability) {
            Log.d(TAG, "Disponibilidade do sensor de calorias alterada: $availability")
        }

        override fun onDataReceived(data: DataPointContainer) {
            exerciseMetrics = exerciseMetrics.update(data)
            val currentTime = System.currentTimeMillis()
            if (currentTime - lastUpdateTime >= measurementInterval * 1000) {
                lastUpdateTime = currentTime
                updateMetricsDisplay()
            }
        }
    }

    private val speedCallback = object : MeasureCallback {
        override fun onAvailabilityChanged(dataType: DeltaDataType<*, *>, availability: Availability) {
            Log.d(TAG, "Disponibilidade do sensor de velocidade alterada: $availability")
        }

        override fun onDataReceived(data: DataPointContainer) {
            exerciseMetrics = exerciseMetrics.update(data)
            val currentTime = System.currentTimeMillis()
            if (currentTime - lastUpdateTime >= measurementInterval * 1000) {
                lastUpdateTime = currentTime
                updateMetricsDisplay()
            }
        }
    }

    private val elevationCallback = object : MeasureCallback {
        override fun onAvailabilityChanged(dataType: DeltaDataType<*, *>, availability: Availability) {
            Log.d(TAG, "Disponibilidade do sensor de elevação alterada: $availability")
        }

        override fun onDataReceived(data: DataPointContainer) {
            exerciseMetrics = exerciseMetrics.update(data)
            val currentTime = System.currentTimeMillis()
            if (currentTime - lastUpdateTime >= measurementInterval * 1000) {
                lastUpdateTime = currentTime
                updateMetricsDisplay()
            }
        }
    }

    private val paceCallback = object : MeasureCallback {
        override fun onAvailabilityChanged(dataType: DeltaDataType<*, *>, availability: Availability) {
            Log.d(TAG, "Disponibilidade do sensor de ritmo alterada: $availability")
        }

        override fun onDataReceived(data: DataPointContainer) {
            exerciseMetrics = exerciseMetrics.update(data)
            val currentTime = System.currentTimeMillis()
            if (currentTime - lastUpdateTime >= measurementInterval * 1000) {
                lastUpdateTime = currentTime
                updateMetricsDisplay()
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        checkPermissions()

        // Obter a referência da aplicação
        mainApplication = application as MainApplication

        // Inicializar cliente de medição
        val healthClient = HealthServices.getClient(this)
        measureClient = healthClient.measureClient

        // Inicializar controles de tempo
        editTextInterval = findViewById(R.id.editTextInterval)
        buttonIncrease = findViewById(R.id.buttonIncrease)
        buttonDecrease = findViewById(R.id.buttonDecrease)
        buttonMqttConfig = findViewById(R.id.buttonMqttConfig)
        switchBackground = findViewById(R.id.switchBackground)
        switchKeepScreenOn = findViewById(R.id.switchKeepScreenOn)
        buttonViewMetrics = findViewById(R.id.buttonViewMetrics)
        
        // Inicializar mapa
        mapView = findViewById(R.id.mapView)
        mapView.onCreate(savedInstanceState)
        mapView.getMapAsync(this)
        
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

        // Inicializa o MeasureClient
        lifecycleScope.launch {
            try {
                // Registrar todos os callbacks de medição necessários
                measureClient.registerMeasureCallback(DataType.HEART_RATE_BPM, heartRateCallback)
                measureClient.registerMeasureCallback(DataType.STEPS, stepsCallback)
                measureClient.registerMeasureCallback(DataType.DISTANCE, distanceCallback)
                measureClient.registerMeasureCallback(DataType.CALORIES, caloriesCallback)
                measureClient.registerMeasureCallback(DataType.SPEED, speedCallback)
                measureClient.registerMeasureCallback(DataType.ELEVATION_GAIN, elevationCallback)
                measureClient.registerMeasureCallback(DataType.PACE, paceCallback)
            } catch (e: Exception) {
                Log.e(TAG, "Erro ao registrar callbacks de medição", e)
            }
        }

        // Inicializa o serviço de localização
        initLocationManager()

        // Registra o receptor de bateria
        registerReceiver(batteryReceiver, IntentFilter(Intent.ACTION_BATTERY_CHANGED))

        // Inicializar botão de visualização de métricas
        buttonViewMetrics.setOnClickListener {
            // Atualizar o LiveData com as métricas atuais
            MetricsActivity.metricsLiveData.value = exerciseMetrics
            // Iniciar a atividade de métricas
            startActivity(Intent(this, MetricsActivity::class.java))
        }
        
        // Inicializar contagem de passos
        lifecycleScope.launch {
            try {
                if (stepCounterService.isGooglePlayServicesAvailable()) {
                    val success = stepCounterService.subscribeToStepCount()
                    if (success) {
                        startStepCountUpdates()
                    } else {
                        Log.e(TAG, "Falha ao iniciar subscrição para contagem de passos")
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Erro ao configurar contagem de passos", e)
            }
        }
    }
    
    private fun initLocationManager() {
        locationManager = getSystemService(Context.LOCATION_SERVICE) as LocationManager
        
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == 
            PackageManager.PERMISSION_GRANTED) {
            
            // Tentar obter localização através do GPS
            if (locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)) {
                locationManager.requestLocationUpdates(
                    LocationManager.GPS_PROVIDER,
                    MIN_TIME_BW_UPDATES,
                    MIN_DISTANCE_CHANGE_FOR_UPDATES,
                    this
                )
                Log.d("MainActivity", "GPS ativado")
                
                val lastKnownLocation = locationManager.getLastKnownLocation(LocationManager.GPS_PROVIDER)
                if (lastKnownLocation != null) {
                    lastLocation = lastKnownLocation
                    updateLocationData(lastKnownLocation)
                }
            }
            
            // Tentar também obter localização através da rede para atualização mais rápida
            if (locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)) {
                locationManager.requestLocationUpdates(
                    LocationManager.NETWORK_PROVIDER,
                    MIN_TIME_BW_UPDATES,
                    MIN_DISTANCE_CHANGE_FOR_UPDATES,
                    this
                )
                Log.d("MainActivity", "Provedor de rede ativado")
            }
        }
    }
    
    private fun updateLocationData(location: Location) {
        val latitude = location.latitude
        val longitude = location.longitude
        
        // Atualizar os dados de métricas
        exerciseMetrics = exerciseMetrics.updateLocation(latitude, longitude)
        
        // Atualizar a exibição
        updateMetricsDisplay()
        
        // Atualizar o mapa
        if (::googleMap.isInitialized) {
            val position = LatLng(latitude, longitude)
            googleMap.clear()
            googleMap.addMarker(MarkerOptions().position(position).title("Localização Atual"))
            googleMap.animateCamera(CameraUpdateFactory.newLatLngZoom(position, 15f))
        }
    }
    
    private fun checkPermissions() {
        // Verificar todas as permissões necessárias logo no início
        if (!hasRequiredPermissions()) {
            // Mostrar explicação sobre a importância das permissões
            showPermissionsExplanationDialog()
        }
    }

    // Mostrar diálogo explicando por que as permissões são necessárias
    private fun showPermissionsExplanationDialog() {
        AlertDialog.Builder(this)
            .setTitle("Permissões Necessárias")
            .setMessage("Este aplicativo precisa das seguintes permissões para funcionar corretamente:\n\n" +
                    "• Sensores Corporais: Para monitorar batimentos cardíacos\n" +
                    "• Sensores em Segundo Plano: Para continuar monitorando quando o app estiver fechado\n" +
                    "• Reconhecimento de Atividade: Para contar passos e detectar movimento\n" +
                    "• Localização: Para registrar seu percurso\n" +
                    "• Serviço em Primeiro Plano: Para manter o app funcionando em segundo plano\n\n" +
                    "Sem essas permissões, o aplicativo não conseguirá monitorar suas métricas de saúde.")
            .setPositiveButton("Solicitar Permissões") { _, _ ->
                requestRequiredPermissions()
            }
            .setNegativeButton("Cancelar") { dialog, _ ->
                dialog.dismiss()
                Toast.makeText(
                    this,
                    "Sem as permissões, alguns recursos não funcionarão corretamente",
                    Toast.LENGTH_LONG
                ).show()
            }
            .setCancelable(false)
            .show()
    }

    // Verificar se todas as permissões necessárias foram concedidas
    private fun hasRequiredPermissions(): Boolean {
        // Verificar a permissão de FOREGROUND_SERVICE_HEALTH (obrigatória)
        val hasForegroundServiceHealth = ActivityCompat.checkSelfPermission(
            this, 
            Manifest.permission.FOREGROUND_SERVICE_HEALTH
        ) == PackageManager.PERMISSION_GRANTED
        
        // Verificar permissões de sensores
        val hasBodySensors = ActivityCompat.checkSelfPermission(
            this,
            Manifest.permission.BODY_SENSORS
        ) == PackageManager.PERMISSION_GRANTED
        
        val hasBodySensorsBackground = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            ActivityCompat.checkSelfPermission(
                this,
                Manifest.permission.BODY_SENSORS_BACKGROUND
            ) == PackageManager.PERMISSION_GRANTED
        } else {
            true // Versões anteriores não precisam dessa permissão específica
        }
        
        val hasActivityRecognition = ActivityCompat.checkSelfPermission(
            this,
            Manifest.permission.ACTIVITY_RECOGNITION
        ) == PackageManager.PERMISSION_GRANTED
        
        val hasHighSamplingRateSensors = ActivityCompat.checkSelfPermission(
            this,
            Manifest.permission.HIGH_SAMPLING_RATE_SENSORS
        ) == PackageManager.PERMISSION_GRANTED
        
        val hasLocation = ActivityCompat.checkSelfPermission(
            this,
            Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        
        val hasForegroundService = ActivityCompat.checkSelfPermission(
            this,
            Manifest.permission.FOREGROUND_SERVICE
        ) == PackageManager.PERMISSION_GRANTED
        
        // Para o aplicativo funcionar minimamente, precisamos:
        // 1. Permissão para serviço em primeiro plano de saúde
        // 2. Permissão para sensores corporais
        // 3. Permissão para reconhecimento de atividade
        // 4. Permissão para localização
        return hasForegroundServiceHealth && hasBodySensors && 
               hasActivityRecognition && hasLocation && 
               hasForegroundService && hasBodySensorsBackground
    }
    
    // Solicitar todas as permissões necessárias
    private fun requestRequiredPermissions() {
        val requiredPermissions = mutableListOf<String>()
        
        // Verificar e adicionar as permissões necessárias
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.FOREGROUND_SERVICE) != 
            PackageManager.PERMISSION_GRANTED) {
            requiredPermissions.add(Manifest.permission.FOREGROUND_SERVICE)
        }
        
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.FOREGROUND_SERVICE_HEALTH) != 
            PackageManager.PERMISSION_GRANTED) {
            requiredPermissions.add(Manifest.permission.FOREGROUND_SERVICE_HEALTH)
        }
        
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.BODY_SENSORS) != 
            PackageManager.PERMISSION_GRANTED) {
            requiredPermissions.add(Manifest.permission.BODY_SENSORS)
        }
        
        // Permissão para sensores em segundo plano (Android 13+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU && 
            ActivityCompat.checkSelfPermission(this, Manifest.permission.BODY_SENSORS_BACKGROUND) != 
            PackageManager.PERMISSION_GRANTED) {
            requiredPermissions.add(Manifest.permission.BODY_SENSORS_BACKGROUND)
        }
        
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.ACTIVITY_RECOGNITION) != 
            PackageManager.PERMISSION_GRANTED) {
            requiredPermissions.add(Manifest.permission.ACTIVITY_RECOGNITION)
        }
        
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.HIGH_SAMPLING_RATE_SENSORS) != 
            PackageManager.PERMISSION_GRANTED) {
            requiredPermissions.add(Manifest.permission.HIGH_SAMPLING_RATE_SENSORS)
        }
        
        // Permissões para localização
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) != 
            PackageManager.PERMISSION_GRANTED) {
            requiredPermissions.add(Manifest.permission.ACCESS_FINE_LOCATION)
        }
        
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_COARSE_LOCATION) != 
            PackageManager.PERMISSION_GRANTED) {
            requiredPermissions.add(Manifest.permission.ACCESS_COARSE_LOCATION)
        }
        
        // Permissão para localização em segundo plano (Android 10+)
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
            
            // Para permissões que precisam ser solicitadas especialmente no Android 11+
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R && 
                requiredPermissions.contains(Manifest.permission.ACCESS_BACKGROUND_LOCATION)) {
                // Esse é um caso especial a partir do Android 11
                // Mostramos instruções para o usuário
                showBackgroundLocationInstructionsDialog()
            }
        } else {
            // Todas as permissões já estão concedidas
            Toast.makeText(this, "Todas as permissões necessárias já estão concedidas", Toast.LENGTH_SHORT).show()
        }
    }
    
    // Mostrar instruções para permissão de localização em segundo plano (Android 11+)
    private fun showBackgroundLocationInstructionsDialog() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            AlertDialog.Builder(this)
                .setTitle("Permissão Adicional Necessária")
                .setMessage("Para monitorar sua localização em segundo plano, é necessário conceder uma permissão adicional nas configurações do aplicativo.\n\n" +
                        "Siga o caminho:\n" +
                        "1. Configurações > Apps > APP_5G_layout\n" +
                        "2. Permissões > Localização\n" +
                        "3. Selecione \"Permitir o tempo todo\"")
                .setPositiveButton("Ir para Configurações") { _, _ ->
                    try {
                        // Abrir configurações do aplicativo
                        val intent = Intent(
                            android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                            android.net.Uri.parse("package:$packageName")
                        )
                        startActivity(intent)
                    } catch (e: Exception) {
                        Log.e(TAG, "Erro ao abrir configurações", e)
                        Toast.makeText(this, "Não foi possível abrir as configurações", Toast.LENGTH_SHORT).show()
                    }
                }
                .setNegativeButton("Depois") { dialog, _ ->
                    dialog.dismiss()
                }
                .show()
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
            val deniedPermissions = mutableListOf<String>()
            
            for (i in permissions.indices) {
                if (grantResults[i] != PackageManager.PERMISSION_GRANTED) {
                    deniedPermissions.add(permissions[i])
                }
            }
            
            if (deniedPermissions.isEmpty()) {
                // Todas as permissões foram concedidas
                Toast.makeText(this, "Todas as permissões concedidas!", Toast.LENGTH_SHORT).show()
                
                // Verificar se o serviço deve ser iniciado
                if (switchBackground.isChecked) {
                    startBackgroundService()
                }
                
                // Iniciar o serviço de localização
                initLocationManager()
            } else {
                // Algumas permissões foram negadas
                Toast.makeText(
                    this,
                    "Algumas permissões foram negadas. Certos recursos podem não funcionar corretamente.",
                    Toast.LENGTH_LONG
                ).show()
                
                // Verificar se há permissões que podemos explicar novamente
                val shouldShowRationale = deniedPermissions.any { 
                    ActivityCompat.shouldShowRequestPermissionRationale(this, it)
                }
                
                if (shouldShowRationale) {
                    // O usuário negou mas não selecionou "Não perguntar novamente"
                    AlertDialog.Builder(this)
                        .setTitle("Permissões Importantes")
                        .setMessage("As permissões negadas são essenciais para o funcionamento completo do aplicativo. Deseja solicitar novamente?")
                        .setPositiveButton("Sim") { _, _ ->
                            requestRequiredPermissions()
                        }
                        .setNegativeButton("Não") { dialog, _ ->
                            dialog.dismiss()
                            // Desmarcar o switch se estiver marcado
                            switchBackground.isChecked = false
                            savePreferences()
                        }
                        .show()
                } else {
                    // O usuário negou e selecionou "Não perguntar novamente"
                    AlertDialog.Builder(this)
                        .setTitle("Permissões Necessárias")
                        .setMessage("Você negou algumas permissões permanentemente. Para que o aplicativo funcione corretamente, é necessário habilitar essas permissões nas configurações do sistema.")
                        .setPositiveButton("Ir para Configurações") { _, _ ->
                            val intent = Intent(
                                android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                                android.net.Uri.parse("package:$packageName")
                            )
                            startActivity(intent)
                        }
                        .setNegativeButton("Cancelar") { dialog, _ ->
                            dialog.dismiss()
                            // Desmarcar o switch se estiver marcado
                            switchBackground.isChecked = false
                            savePreferences()
                        }
                        .show()
                }
            }
        }
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
        
        // Retomar o mapa
        mapView.onResume()
        
        // Verificar status do MQTT e atualizar a UI se necessário
        if (mainApplication.mqttHandler.isConnected()) {
            // Se estiver conectado, iniciar a publicação de medições
            startMqttPublishing()
        }
    }

    override fun onPause() {
        super.onPause()
        // Pausar o mapa
        mapView.onPause()
    }

    override fun onDestroy() {
        super.onDestroy()
        // Parar a atualização de localização
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == 
            PackageManager.PERMISSION_GRANTED) {
            locationManager.removeUpdates(this)
        }
        
        // Limpar callbacks de medição
        lifecycleScope.launch {
            try {
                // Removido a chamada para clearMeasureCallbacks que não existe na versão atual
                Log.d("MainActivity", "Encerrando callbacks de medição")
            } catch (e: Exception) {
                Log.e("MainActivity", "Erro ao limpar callbacks", e)
            }
        }
        
        // Destruir o mapa
        mapView.onDestroy()
        
        // Desregistra o receptor de bateria quando a atividade é destruída
        unregisterReceiver(batteryReceiver)
    }
    
    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        mapView.onSaveInstanceState(outState)
    }

    override fun onLowMemory() {
        super.onLowMemory()
        mapView.onLowMemory()
    }
    
    // Iniciar a publicação periódica de dados MQTT
    private fun startMqttPublishing() {
        // Fornecer funções que retornam os dados mais recentes
        mainApplication.startMqttPublishing(
            heartRateProvider = { exerciseMetrics.heartRate },
            batteryLevelProvider = { exerciseMetrics.batteryLevel },
            locationProvider = { Pair(exerciseMetrics.latitude, exerciseMetrics.longitude) },
            secondsMeasureProvider = { measurementInterval }
        )
    }

    // Callback de mapa pronto
    override fun onMapReady(map: GoogleMap) {
        googleMap = map
        
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == 
            PackageManager.PERMISSION_GRANTED) {
            googleMap.isMyLocationEnabled = true
            
            if (lastLocation != null) {
                val position = LatLng(lastLocation!!.latitude, lastLocation!!.longitude)
                googleMap.addMarker(MarkerOptions().position(position).title("Localização Atual"))
                googleMap.moveCamera(CameraUpdateFactory.newLatLngZoom(position, 15f))
            }
        }
        
        // Configurar o mapa para zoom máximo e UI mínima (ideal para relógios)
        googleMap.uiSettings.apply {
            isZoomControlsEnabled = false
            isCompassEnabled = false
            isMyLocationButtonEnabled = false
            isRotateGesturesEnabled = false
            isScrollGesturesEnabled = false
        }
    }

    // Callbacks de LocationListener
    override fun onLocationChanged(location: Location) {
        lastLocation = location
        updateLocationData(location)
    }

    private fun startStepCountUpdates() {
        lifecycleScope.launch {
            while (true) {
                try {
                    val steps = stepCounterService.readStepCountData()
                    if (steps > 0) {
                        // Atualiza passos e calcula distância e calorias com base neles
                        exerciseMetrics = exerciseMetrics.updateSteps(steps)
                            .calculateDistanceFromSteps()
                            .calculateCaloriesFromSteps()
                        
                        // Atualizar a interface (ViewPager, etc)
                        updateMetrics()
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Erro ao ler contagem de passos", e)
                }
                delay(60000) // Atualiza a cada minuto
            }
        }
    }

    private fun updateMetrics() {
        // Atualizar o LiveData para a MetricsActivity
        runOnUiThread {
            MetricsActivity.metricsLiveData.postValue(exerciseMetrics)
        }
    }
}