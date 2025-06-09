package com.example.mqttwearable.mqtt
import android.content.Context
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import org.eclipse.paho.client.mqttv3.MqttClient
import org.eclipse.paho.client.mqttv3.MqttConnectOptions
import org.eclipse.paho.client.mqttv3.MqttException
import org.eclipse.paho.client.mqttv3.MqttMessage
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence
import org.eclipse.paho.client.mqttv3.IMqttActionListener
import org.eclipse.paho.client.mqttv3.IMqttDeliveryToken
import org.eclipse.paho.client.mqttv3.IMqttToken
import org.eclipse.paho.client.mqttv3.MqttCallback
import android.util.Log

//sudo nano /etc/mosquitto/mosquitto.conf
//# Permite conexões de qualquer IP (não apenas localhost)
//listener 1883 0.0.0.0
//
//# Habilita autenticação anônima (apenas para testes)
//allow_anonymous true
//

//cmd
//No servidor (Windows):
//Verifique se o Mosquitto está rodando:
//
//cmd
//netstat -ano | findstr 1883
//(Deve aparecer 0.0.0.0:1883).
//netstat -ano | findstr 1883
//A saída deve mostrar:
//
//TCP    0.0.0.0:1883          0.0.0.0:0              LISTENING       <PID>
//TCP    [::]:1883             [::]:0                 LISTENING       <PID>
////netsh advfirewall firewall add rule name="MQTT" dir=in action=allow protocol=TCP localport=1883
//mosquitto -v -c mosquitto.conf
//mosquitto_sub -h 192.168.68.102 -p 1883 -t "teste" -v
//>mosquitto_pub -h 192.168.68.102 -p 1883 -t teste -m ok
// adb connect 192.168.68.112:41751
// adb -s 192.168.68.123:41751 install -r app/build/outputs/apk/debug/app-debug.apk
//PS C:\Users\lmhon\Dropbox\Projetos\Sto Antonio 5.0\MqttHealth> adb -s 192.168.68.112:42601 logcat  -c
//PS C:\Users\lmhon\Dropbox\Projetos\Sto Antonio 5.0\MqttHealth> adb -s 192.168.68.112:42601 logcat HealthPublisher:D *:S




class MqttHandler(private val context: Context) {
    private var client: MqttClient? = null
    private var isConnected = false

    fun connect(brokerUrl: String, clientId: String, callback: (Boolean) -> Unit) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val persistence = MemoryPersistence()
                client = MqttClient(brokerUrl, clientId, persistence).apply {
                    val options = MqttConnectOptions().apply {
                        isCleanSession = true
                        connectionTimeout = 10
                        keepAliveInterval = 20
                    }
                    connect(options)
                    this@MqttHandler.isConnected = true
                    Log.d("MqttHandler", "Connected to $brokerUrl")
                    callback(true)
                }
            } catch (e: MqttException) {
                Log.e("MqttHandler", "Connection failed", e)
                callback(false)
            }
        }
    }

    fun disconnect() {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                client?.disconnect()
                isConnected = false
                Log.d("MqttHandler", "Disconnected")
            } catch (e: MqttException) {
                Log.e("MqttHandler", "Disconnect failed", e)
            }
        }
    }

    fun publish(topic: String, message: String, callback: (Boolean) -> Unit = { _ -> }) {
        if (!isConnected) {
            Log.e("MqttHandler", "Not connected, cannot publish")
            callback(false)
            return
        }

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val mqttMessage = MqttMessage(message.toByteArray())
                client?.publish(topic, mqttMessage)
                Log.d("MqttHandler", "Published to $topic: $message")
                callback(true)
            } catch (e: MqttException) {
                Log.e("MqttHandler", "Publish failed", e)
                callback(false)
            }
        }
    }

    fun subscribe(topic: String, callback: (String) -> Unit) {
        if (!isConnected) {
            Log.e("MqttHandler", "Not connected, cannot subscribe")
            return
        }

        CoroutineScope(Dispatchers.IO).launch {
            try {
                client?.setCallback(object : MqttCallback {
                    override fun connectionLost(cause: Throwable) {
                        Log.e("MqttHandler", "Connection lost", cause)
                        isConnected = false
                    }

                    override fun messageArrived(topic: String, message: MqttMessage) {
                        val payload = String(message.payload)
                        Log.d("MqttHandler", "Message arrived on $topic: $payload")
                        callback(payload)
                    }

                    override fun deliveryComplete(token: IMqttDeliveryToken) {
                        Log.d("MqttHandler", "Message delivered")
                    }
                })
                client?.subscribe(topic)
                Log.d("MqttHandler", "Subscribed to $topic")
            } catch (e: MqttException) {
                Log.e("MqttHandler", "Subscribe failed", e)
            }
        }
    }
}
