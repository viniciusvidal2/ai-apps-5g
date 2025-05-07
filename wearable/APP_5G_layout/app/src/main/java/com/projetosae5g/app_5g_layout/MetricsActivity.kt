package com.projetosae5g.app_5g_layout

import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.viewpager2.widget.ViewPager2
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.Observer

class MetricsActivity : ComponentActivity() {
    
    private lateinit var viewPagerMetrics: ViewPager2
    private lateinit var metricPagerAdapter: MetricPagerAdapter
    
    // LiveData para receber atualizações de métricas
    companion object {
        val metricsLiveData = MutableLiveData<ExerciseMetrics>()
        private const val TAG = "MetricsActivity"
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_metrics)
        
        // Inicializar ViewPager
        viewPagerMetrics = findViewById(R.id.viewPagerAllMetrics)
        metricPagerAdapter = MetricPagerAdapter(
            listOf(
                "BATIMENTOS CARDÍACOS: --",
                "PASSOS: --",
                "DISTÂNCIA: -- m",
                "CALORIAS: -- kcal",
                "VELOCIDADE: -- m/s",
                "ELEVAÇÃO: -- m",
                "RITMO: -- min/km",
                "LOCALIZAÇÃO: --, --",
                "NÍVEL DA BATERIA: --%"
            )
        )
        viewPagerMetrics.adapter = metricPagerAdapter
        viewPagerMetrics.orientation = ViewPager2.ORIENTATION_VERTICAL
        
        // Observar mudanças nas métricas
        metricsLiveData.observe(this, Observer { metrics ->
            updateMetricsDisplay(metrics)
        })
    }
    
    private fun updateMetricsDisplay(metrics: ExerciseMetrics) {
        val metricsList = listOf(
            "BATIMENTOS CARDÍACOS: ${metrics.heartRate ?: "--"} BPM",
            "PASSOS: ${metrics.steps ?: "--"}",
            "DISTÂNCIA: ${String.format("%.2f", metrics.distance ?: 0.0)} m",
            "CALORIAS: ${String.format("%.1f", metrics.calories ?: 0.0)} kcal",
            "VELOCIDADE: ${String.format("%.1f", metrics.speed ?: 0.0)} m/s",
            "ELEVAÇÃO: ${String.format("%.1f", metrics.elevation ?: 0.0)} m",
            "RITMO: ${String.format("%.1f", metrics.pace ?: 0.0)} min/km",
            "LOCALIZAÇÃO: ${String.format("%.5f", metrics.latitude ?: 0.0)}, ${String.format("%.5f", metrics.longitude ?: 0.0)}",
            "NÍVEL DA BATERIA: ${metrics.batteryLevel ?: "--"}%"
        )
        
        runOnUiThread {
            metricPagerAdapter.updateMetrics(metricsList)
        }
    }
} 