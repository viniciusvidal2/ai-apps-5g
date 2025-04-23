package com.projetosae5g.app_5g_layout

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.os.Build
import android.util.Log

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            Log.d("BootReceiver", "Dispositivo inicializado, verificando se o serviço deve ser iniciado")
            
            // Verificar preferências para determinar se o serviço deve ser iniciado automaticamente
            val sharedPreferences = context.getSharedPreferences("service_prefs", Context.MODE_PRIVATE)
            val shouldStartService = sharedPreferences.getBoolean("service_auto_start", false)
            
            if (shouldStartService) {
                Log.d("BootReceiver", "Iniciando serviço de monitoramento após inicialização")
                
                // Obter intervalo de medição salvo anteriormente
                val interval = sharedPreferences.getLong("measurement_interval", 60)
                
                // Iniciar o serviço
                val serviceIntent = Intent(context, MonitorService::class.java).apply {
                    putExtra("interval", interval)
                }
                
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    context.startForegroundService(serviceIntent)
                } else {
                    context.startService(serviceIntent)
                }
            }
        }
    }
} 