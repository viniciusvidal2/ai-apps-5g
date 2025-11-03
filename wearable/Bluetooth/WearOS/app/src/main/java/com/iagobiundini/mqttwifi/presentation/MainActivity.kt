package com.iagoBiundini.mqttwifi.presentation

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.bluetooth.le.BluetoothLeScanner
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanResult
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.Button
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import com.iagoBiundini.mqttwifi.R
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.UUID

class MainActivity : ComponentActivity() {

    // UI Components
    private lateinit var connectButton: Button
    private lateinit var statusTextView: TextView

    // Bluetooth Components
    private var bluetoothAdapter: BluetoothAdapter? = null
    private var bluetoothLeScanner: BluetoothLeScanner? = null
    private var bluetoothGatt: BluetoothGatt? = null
    private var targetDevice: BluetoothDevice? = null

    // Constants
    private val TARGET_DEVICE_NAME = "ESP32_Usina5G"
    private val SERVICE_UUID = UUID.fromString("0000FFE0-0000-1000-8000-00805F9B34FB")
    private val CHARACTERISTIC_UUID = UUID.fromString("0000FFE1-0000-1000-8000-00805F9B34FB")
    private val SCAN_PERIOD: Long = 10000 // 10 segundos

    private val handler = Handler(Looper.getMainLooper())
    private var isScanning = false

    // Permission Launcher
    private val requestPermissionsLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val allGranted = permissions.entries.all { it.value }
        if (allGranted) {
            startBluetoothProcess()
        } else {
            updateStatus(getString(R.string.status_permission_required))
            enableButton()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        // Initialize UI
        connectButton = findViewById(R.id.connectButton)
        statusTextView = findViewById(R.id.statusTextView)

        // Initialize Bluetooth
        val bluetoothManager = getSystemService(BLUETOOTH_SERVICE) as BluetoothManager
        bluetoothAdapter = bluetoothManager.adapter
        bluetoothLeScanner = bluetoothAdapter?.bluetoothLeScanner

        // Button Click Listener
        connectButton.setOnClickListener {
            if (checkPermissions()) {
                disableButton()
                startBluetoothProcess()
            } else {
                requestPermissions()
            }
        }
    }

    private fun checkPermissions(): Boolean {
        val requiredPermissions = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            arrayOf(
                Manifest.permission.BLUETOOTH_SCAN,
                Manifest.permission.BLUETOOTH_CONNECT,
                Manifest.permission.ACCESS_FINE_LOCATION
            )
        } else {
            arrayOf(
                Manifest.permission.BLUETOOTH,
                Manifest.permission.BLUETOOTH_ADMIN,
                Manifest.permission.ACCESS_FINE_LOCATION
            )
        }

        return requiredPermissions.all {
            ContextCompat.checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED
        }
    }

    private fun requestPermissions() {
        val requiredPermissions = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            arrayOf(
                Manifest.permission.BLUETOOTH_SCAN,
                Manifest.permission.BLUETOOTH_CONNECT,
                Manifest.permission.ACCESS_FINE_LOCATION
            )
        } else {
            arrayOf(
                Manifest.permission.BLUETOOTH,
                Manifest.permission.BLUETOOTH_ADMIN,
                Manifest.permission.ACCESS_FINE_LOCATION
            )
        }

        requestPermissionsLauncher.launch(requiredPermissions)
    }

    private fun startBluetoothProcess() {
        if (bluetoothAdapter == null || !bluetoothAdapter!!.isEnabled) {
            updateStatus(getString(R.string.status_error, "Bluetooth desativado"))
            enableButton()
            return
        }

        scanForDevices()
    }

    private fun scanForDevices() {
        if (ActivityCompat.checkSelfPermission(
                this,
                Manifest.permission.BLUETOOTH_SCAN
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            return
        }

        updateStatus(getString(R.string.status_scanning))

        if (isScanning) {
            bluetoothLeScanner?.stopScan(leScanCallback)
        }

        isScanning = true
        bluetoothLeScanner?.startScan(leScanCallback)

        // Stop scan after SCAN_PERIOD
        handler.postDelayed({
            if (isScanning) {
                isScanning = false
                if (ActivityCompat.checkSelfPermission(
                        this,
                        Manifest.permission.BLUETOOTH_SCAN
                    ) == PackageManager.PERMISSION_GRANTED
                ) {
                    bluetoothLeScanner?.stopScan(leScanCallback)
                }
                
                if (targetDevice == null) {
                    updateStatus(getString(R.string.status_device_not_found))
                    enableButton()
                }
            }
        }, SCAN_PERIOD)
    }

    private val leScanCallback = object : ScanCallback() {
        override fun onScanResult(callbackType: Int, result: ScanResult) {
            super.onScanResult(callbackType, result)

            if (ActivityCompat.checkSelfPermission(
                    this@MainActivity,
                    Manifest.permission.BLUETOOTH_CONNECT
                ) != PackageManager.PERMISSION_GRANTED
            ) {
                return
            }

            val device = result.device
            val deviceName = device.name

            if (deviceName == TARGET_DEVICE_NAME && targetDevice == null) {
                targetDevice = device
                isScanning = false
                bluetoothLeScanner?.stopScan(this)
                connectToDevice(device)
            }
        }

        override fun onScanFailed(errorCode: Int) {
            super.onScanFailed(errorCode)
            updateStatus(getString(R.string.status_error, "Scan falhou: $errorCode"))
            enableButton()
        }
    }

    private fun connectToDevice(device: BluetoothDevice) {
        if (ActivityCompat.checkSelfPermission(
                this,
                Manifest.permission.BLUETOOTH_CONNECT
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            return
        }

        updateStatus(getString(R.string.status_connecting))
        bluetoothGatt = device.connectGatt(this, false, gattCallback)
    }

    private val gattCallback = object : BluetoothGattCallback() {
        override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
            if (newState == BluetoothProfile.STATE_CONNECTED) {
                runOnUiThread {
                    updateStatus(getString(R.string.status_connected))
                }

                if (ActivityCompat.checkSelfPermission(
                        this@MainActivity,
                        Manifest.permission.BLUETOOTH_CONNECT
                    ) != PackageManager.PERMISSION_GRANTED
                ) {
                    return
                }

                // Discover services
                gatt.discoverServices()

            } else if (newState == BluetoothProfile.STATE_DISCONNECTED) {
                runOnUiThread {
                    updateStatus(getString(R.string.status_error, "Desconectado"))
                    enableButton()
                }
                cleanup()
            }
        }

        override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) {
            if (status == BluetoothGatt.GATT_SUCCESS) {
                val service = gatt.getService(SERVICE_UUID)
                val characteristic = service?.getCharacteristic(CHARACTERISTIC_UUID)

                if (characteristic != null) {
                    runOnUiThread {
                        updateStatus(getString(R.string.status_sending))
                    }
                    sendTimeData(gatt, characteristic)
                } else {
                    runOnUiThread {
                        updateStatus(getString(R.string.status_error, "Característica não encontrada"))
                        enableButton()
                    }
                    cleanup()
                }
            } else {
                runOnUiThread {
                    updateStatus(getString(R.string.status_error, "Falha ao descobrir serviços"))
                    enableButton()
                }
                cleanup()
            }
        }

        override fun onCharacteristicWrite(
            gatt: BluetoothGatt,
            characteristic: BluetoothGattCharacteristic,
            status: Int
        ) {
            if (status == BluetoothGatt.GATT_SUCCESS) {
                runOnUiThread {
                    updateStatus(getString(R.string.status_success))
                    enableButton()
                }
            } else {
                runOnUiThread {
                    updateStatus(getString(R.string.status_error, "Falha ao enviar dados"))
                    enableButton()
                }
            }
            
            // Disconnect after sending
            handler.postDelayed({
                cleanup()
            }, 2000)
        }
    }

    @Suppress("DEPRECATION")
    private fun sendTimeData(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic) {
        if (ActivityCompat.checkSelfPermission(
                this,
                Manifest.permission.BLUETOOTH_CONNECT
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            return
        }

        // Get current time
        val dateFormat = SimpleDateFormat("HH:mm:ss dd/MM/yyyy", Locale.getDefault())
        val currentTime = dateFormat.format(Date())

        // Set characteristic value and write
        val timeBytes = currentTime.toByteArray(Charsets.UTF_8)
        characteristic.value = timeBytes
        gatt.writeCharacteristic(characteristic)
    }

    private fun updateStatus(message: String) {
        runOnUiThread {
            statusTextView.text = message
        }
    }

    private fun disableButton() {
        connectButton.isEnabled = false
    }

    private fun enableButton() {
        connectButton.isEnabled = true
    }

    private fun cleanup() {
        if (ActivityCompat.checkSelfPermission(
                this,
                Manifest.permission.BLUETOOTH_CONNECT
            ) == PackageManager.PERMISSION_GRANTED
        ) {
            bluetoothGatt?.disconnect()
            bluetoothGatt?.close()
        }
        bluetoothGatt = null
        targetDevice = null
    }

    override fun onDestroy() {
        super.onDestroy()
        cleanup()
        if (isScanning) {
            if (ActivityCompat.checkSelfPermission(
                    this,
                    Manifest.permission.BLUETOOTH_SCAN
                ) == PackageManager.PERMISSION_GRANTED
            ) {
                bluetoothLeScanner?.stopScan(leScanCallback)
            }
        }
    }
}
