package com.iagoBiundini.mqttwifi.utils

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities

object NetworkUtils {
    
    /**
     * Verifica se o dispositivo está conectado à rede WiFi
     * @param context Contexto da aplicação
     * @return true se conectado ao WiFi, false caso contrário
     */
    fun isWifiConnected(context: Context): Boolean {
        val connectivityManager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        
        val network = connectivityManager.activeNetwork ?: return false
        val capabilities = connectivityManager.getNetworkCapabilities(network) ?: return false
        
        return capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)
    }
    
    /**
     * Obtém o nome da rede WiFi conectada (se disponível)
     */
    fun getWifiNetworkName(context: Context): String? {
        val connectivityManager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val network = connectivityManager.activeNetwork ?: return null
        val capabilities = connectivityManager.getNetworkCapabilities(network) ?: return null
        
        return if (capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) {
            "WiFi Connected"
        } else {
            null
        }
    }
}
