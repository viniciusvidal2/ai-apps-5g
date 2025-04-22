package com.projetosae5g.app_5g_layout

import android.Manifest
import android.content.pm.PackageManager
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
    private var measurementInterval: Long = 1 // segundos
    private var lastUpdateTime: Long = 0  // em milissegundos

    // ViewPager2 e adapter para métricas
    private lateinit var viewPagerMetrics: ViewPager2
    private lateinit var metricPagerAdapter: MetricPagerAdapter

    // Callback de medição
    private val heartRateCallback = object : MeasureCallback {
        override fun onDataReceived(data: DataPointContainer) {
            // Atualiza os dados já conhecidos (apenas alguns são extraídos da API)
            exerciseMetrics = exerciseMetrics.update(data)
            val currentTime = System.currentTimeMillis()
            if (currentTime - lastUpdateTime >= measurementInterval * 1000) {
                lastUpdateTime = currentTime
                val metricsList = listOf(
                    "HEART_RATE_BPM: ${exerciseMetrics.heartRate ?: "--"}",
                    "CALORIAS: ${exerciseMetrics.calories ?: "--"}",
                    "CALORIES_DAILY: ${exerciseMetrics.caloriesDaily ?: "--"}",
                    "DISTÂNCIA_DAILY: ${exerciseMetrics.distanceDaily ?: "--"}",
                    "DECLINE_DIST: ${exerciseMetrics.declineDist ?: "--"}",
                    "DISTÂNCIA: ${exerciseMetrics.distance ?: "--"}",
                    "ELEVATION_GAIN: ${exerciseMetrics.elevationGain ?: "--"}",
                    "ELEVATION_LOSS: ${exerciseMetrics.elevationLoss ?: "--"}",
                    "FLAT_GROUND_DIST: ${exerciseMetrics.flatGroundDist ?: "--"}",
                    "Andares: ${exerciseMetrics.floors ?: "--"}",
                    "FLOORS_DAILY: ${exerciseMetrics.floorsDaily ?: "--"}",
                    "GOLF_SHOT_COUNT: ${exerciseMetrics.golfShotCount ?: "--"}",
                    "INCLINE_DIST: ${exerciseMetrics.inclineDist ?: "--"}",
                    "RITMO: ${exerciseMetrics.ritmo ?: "--"}",
                    "REP_COUNT: ${exerciseMetrics.repCount ?: "--"}",
                    "ETAPAS EM EXECUÇÃO: ${exerciseMetrics.executingStages ?: "--"}",
                    "VELOCIDADE: ${exerciseMetrics.velocity ?: "--"}",
                    "ETAPAS: ${exerciseMetrics.stages ?: "--"}",
                    "STEPS_DAILY: ${exerciseMetrics.stepsDaily ?: "--"}",
                    "ETAPAS_PER_MINUTO: ${exerciseMetrics.stagesPerMinute ?: "--"}",
                    "SWIMMING_LAP_COUNT: ${exerciseMetrics.swimmingLapCount ?: "--"}",
                    "SWIMMING_STROKES: ${exerciseMetrics.swimmingStrokes ?: "--"}",
                    "CALORIES_TOTAL: ${exerciseMetrics.caloriesTotal ?: "--"}",
                    "WALKING_STEPS: ${exerciseMetrics.walkingSteps ?: "--"}",
                    "UserActivityInfo: ${exerciseMetrics.userActivityInfo ?: "--"}",
                    "UserActivityState: ${exerciseMetrics.userActivityState ?: "--"}",
                    "ACTIVITY_RECOGNITION: ${exerciseMetrics.activityRecognition ?: "--"}",
                    "VO2_MAX: ${exerciseMetrics.vo2Max ?: "--"}",
                    "ELEVAÇÃO ABSOLUTA: ${exerciseMetrics.elevationAbsolute ?: "--"}",
                    "LOCAL: ${exerciseMetrics.local ?: "--"}",
                )
                runOnUiThread {
                    metricPagerAdapter.updateMetrics(metricsList)
                }
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

        // Inicializa controles de tempo
        editTextInterval = findViewById(R.id.editTextInterval)
        buttonIncrease = findViewById(R.id.buttonIncrease)
        buttonDecrease = findViewById(R.id.buttonDecrease)

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

        // Inicializa ViewPager2 e adapter com valores iniciais (todos “--”)
        viewPagerMetrics = findViewById(R.id.viewPagerMetrics)
        metricPagerAdapter = MetricPagerAdapter(
            listOf(
                "HEART_RATE_BPM: --",
                "CALORIAS: --",
                "CALORIES_DAILY: --",
                "DISTÂNCIA_DAILY: --",
                "DECLINE_DIST: --",
                "DISTÂNCIA: --",
                "ELEVATION_GAIN: --",
                "ELEVATION_LOSS: --",
                "FLAT_GROUND_DIST: --",
                "Andares: --",
                "FLOORS_DAILY: --",
                "GOLF_SHOT_COUNT: --",
                "INCLINE_DIST: --",
                "RITMO: --",
                "REP_COUNT: --",
                "ETAPAS EM EXECUÇÃO: --",
                "VELOCIDADE: --",
                "ETAPAS: --",
                "STEPS_DAILY: --",
                "ETAPAS_PER_MINUTO: --",
                "SWIMMING_LAP_COUNT: --",
                "SWIMMING_STROKES: --",
                "CALORIES_TOTAL: --",
                "WALKING_STEPS: --",
                "UserActivityInfo: --",
                "UserActivityState: --",
                "VO2_MAX: --",
                "ELEVAÇÃO ABSOLUTA: --",
                "LOCAL: --",
                "ACCESS_FINE_LOCATION: --"
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
    }

    override fun onResume() {
        super.onResume()
    }

    override fun onPause() {
        super.onPause()
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
