/* While this template provides a good starting point for using Wear Compose, you can always
 * take a look at https://github.com/android/wear-os-samples/tree/main/ComposeStarter to find the
 * most up to date changes to the libraries and their usages.
 */

package com.example.mqttwearable.presentation

import android.annotation.SuppressLint
import android.app.NotificationChannel
import android.app.NotificationManager
import android.view.WindowManager

import android.content.Context
import android.content.Intent
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.view.GestureDetector
import android.view.MotionEvent
import android.view.View
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.compose.ui.platform.LocalContext

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.wear.compose.material.MaterialTheme
import androidx.wear.compose.material.Text
import androidx.wear.compose.material.TimeText
import androidx.wear.tooling.preview.devices.WearDevices
import androidx.compose.runtime.mutableStateOf
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Spacer
import androidx.wear.compose.material.Button
import androidx.compose.foundation.layout.height
import androidx.compose.ui.unit.dp
import android.util.Log
import androidx.wear.compose.material.ButtonDefaults
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import org.eclipse.paho.client.mqttv3.MqttClient
import org.eclipse.paho.client.mqttv3.MqttConnectOptions
import org.eclipse.paho.client.mqttv3.MqttMessage
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import androidx.compose.runtime.remember
import androidx.health.services.client.data.DataType
import androidx.health.services.client.data.DeltaDataType
import androidx.lifecycle.lifecycleScope
import com.example.mqttwearable.R
import com.example.mqttwearable.mqtt.MqttHandler
import com.example.mqttwearable.health.HealthPublisher
import androidx.activity.result.contract.ActivityResultContracts.RequestMultiplePermissions
import androidx.activity.result.ActivityResultLauncher
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.example.mqttwearable.health.HealthForegroundService
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.text.InputFilter
import android.provider.Settings
import com.example.mqttwearable.data.DeviceIdManager


class MainActivity : ComponentActivity() {

    private lateinit var mqttHandler: MqttHandler
    private lateinit var healthPublisher: HealthPublisher

    // Indica se o MQTT está conectado
    private var mqttConnected by mutableStateOf(false)

    private val requiredPermissions = arrayOf(
        android.Manifest.permission.ACTIVITY_RECOGNITION,
        android.Manifest.permission.BODY_SENSORS,
        android.Manifest.permission.ACCESS_FINE_LOCATION,
        android.Manifest.permission.ACCESS_COARSE_LOCATION
    )

    // 2) Crie o launcher que vai pedir essas permissões
    private lateinit var permissionsLauncher: ActivityResultLauncher<Array<String>>

    // Detector de gestos para capturar o swipe down
    private lateinit var gestureDetector: GestureDetector



//    val activeTypes: Set<DeltaDataType<*, *>> = setOf(
////        DataType.STEPS,     // é um DeltaDataType<Int, SampleDataPoint<Int>>
////        DataType.CALORIES,  // é um DeltaDataType<Float, SampleDataPoint<Float>>
////        DataType.DISTANCE,   // é um DeltaDataType<Float, SampleDataPoint<Float>>
//        DataType.PACE,   // é um DeltaDataType<Float, SampleDataPoint<Float>>
//        DataType.HEART_RATE_BPM
////        DataType.ABSOLUTE_ELEVATION
//    )



    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()

        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        // Inicializar o DeviceIdManager
        DeviceIdManager.initializeDeviceId(this)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationManagerCompat.from(this).createNotificationChannel(
                NotificationChannel(
                    HealthForegroundService.CHANNEL_ID,
                    "Serviço de Saúde",
                    NotificationManager.IMPORTANCE_LOW
                )
            )
        }

        setTheme(android.R.style.Theme_DeviceDefault)

        mqttHandler = MqttHandler(applicationContext)
        healthPublisher = HealthPublisher(applicationContext, mqttHandler)

        setContentView(R.layout.activity_main)

        // Configurar detector de gestos
        setupGestureDetector()

        val txtAndroidId = findViewById<TextView>(R.id.txtAndroidId)
        val edtIp = findViewById<EditText>(R.id.edtIp)
        val btnConectar = findViewById<Button>(R.id.btnConectar)
        val btnAcc = findViewById<Button>(R.id.btnAcc)
        val btnSpO2 = findViewById<Button>(R.id.btnSpO2)
        val txtStatus = findViewById<TextView?>(R.id.txtStatus)
        
        // Obter e exibir o ANDROID_ID usando o DeviceIdManager
        txtAndroidId.text = DeviceIdManager.getDeviceId()
        
        txtStatus?.text = "Desconectado"
        var isConnected = false
        btnConectar.text = "Conectar"

        btnConectar.setOnClickListener {
            if (!isConnected) {
                val ipText = edtIp.text.toString().trim()
                if (ipText.isEmpty()) {
                    txtStatus?.text = "Por favor, insira o IP do broker MQTT."
                    return@setOnClickListener
                }
                permissionsLauncher.launch(requiredPermissions)
            } else {
                mqttHandler.disconnect()
                isConnected = false
                mqttConnected = false
                btnConectar.text = "Conectar"
                txtStatus?.text = "Desconectado"
            }
        }

        btnAcc.setOnClickListener {
            // Navegar para a tela de acelerômetro
            val intent = Intent(this, AccelerometerActivity::class.java)
            // Passar o IP do broker MQTT se estiver conectado
            val ipText = edtIp.text.toString().trim()
            if (ipText.isNotEmpty()) {
                intent.putExtra("BROKER_IP", ipText)
            }
            startActivity(intent)
        }

        btnSpO2.setOnClickListener {
            // Navegar para a tela de SpO2
            val intent = Intent(this, SpO2Activity::class.java)
            startActivity(intent)
        }

        permissionsLauncher = registerForActivityResult(RequestMultiplePermissions()) { results ->
            if (results.values.all { it }) {
                val ipText = edtIp.text.toString().trim()
                if (ipText.isEmpty()) {
                    txtStatus?.text = "Por favor, insira o IP do broker MQTT."
                    return@registerForActivityResult
                }
                val brokerUrl = "tcp://$ipText:1883"
                mqttHandler.connect(
                    brokerUrl = brokerUrl,
                    clientId = "wearable-${System.currentTimeMillis()}"
                ) { success ->
                    mqttConnected = success
                    isConnected = success
                    runOnUiThread {
                        if (success) {
                            btnConectar.text = "Desconectar"
                            txtStatus?.text = "MQTT conectado com sucesso"
                        } else {
                            btnConectar.text = "Conectar"
                            txtStatus?.text = "Falha ao conectar MQTT"
                        }
                    }
                    if (success) {
                        Log.d("MainActivity", "MQTT conectado com sucesso")
                        lifecycleScope.launch {
                            healthPublisher.startPassiveMeasure()
                        }
                        val intent = Intent(this, HealthForegroundService::class.java)
                        ContextCompat.startForegroundService(this, intent)
                    } else {
                        Log.e("MainActivity", "Falha ao conectar MQTT")
                    }
                }
            } else {
                Log.e("MainActivity", "Permissões de Health Services não concedidas")
            }
        }
    }


    override fun onStart() {
        super.onStart()

        permissionsLauncher.launch(requiredPermissions)

    }

    @SuppressLint("ImplicitSamInstance")
    override fun onStop() {
        super.onStop()
    }

    override fun onDestroy() {
        super.onDestroy()
    }

    private fun setupGestureDetector() {
        gestureDetector = GestureDetector(this, object : GestureDetector.SimpleOnGestureListener() {
            private val SWIPE_THRESHOLD = 100
            private val SWIPE_VELOCITY_THRESHOLD = 100

            override fun onFling(
                e1: MotionEvent?,
                e2: MotionEvent,
                velocityX: Float,
                velocityY: Float
            ): Boolean {
                if (e1 == null) return false
                
                val diffY = e2.y - e1.y
                val diffX = e2.x - e1.x
                
                if (Math.abs(diffY) > Math.abs(diffX)) {
                    if (Math.abs(diffY) > SWIPE_THRESHOLD && Math.abs(velocityY) > SWIPE_VELOCITY_THRESHOLD) {
                        if (diffY > 0) {
                            // Swipe para baixo - abrir tela de acelerômetro
                            onSwipeDown()
                            return true
                        }
                    }
                }
                return false
            }
        })

        // Aplicar o detector de gestos à view raiz
        findViewById<View>(android.R.id.content).setOnTouchListener { _, event ->
            gestureDetector.onTouchEvent(event)
        }
    }

    private fun onSwipeDown() {
        // Navegar para a tela de acelerômetro
        val intent = Intent(this, AccelerometerActivity::class.java)
        // Passar o IP do broker MQTT se estiver conectado
        val edtIp = findViewById<EditText>(R.id.edtIp)
        val ipText = edtIp.text.toString().trim()
        if (ipText.isNotEmpty()) {
            intent.putExtra("BROKER_IP", ipText)
        }
        startActivity(intent)
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        return gestureDetector.onTouchEvent(event) || super.onTouchEvent(event)
    }
}