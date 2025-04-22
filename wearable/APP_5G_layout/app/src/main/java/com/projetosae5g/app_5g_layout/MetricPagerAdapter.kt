package com.projetosae5g.app_5g_layout

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

class MetricPagerAdapter(private var metrics: List<String>) :
    RecyclerView.Adapter<MetricPagerAdapter.MetricViewHolder>() {

    class MetricViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val textViewMetric: TextView = itemView.findViewById(R.id.textViewMetric)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): MetricViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_metric, parent, false)
        return MetricViewHolder(view)
    }

    override fun onBindViewHolder(holder: MetricViewHolder, position: Int) {
        holder.textViewMetric.text = metrics[position]
    }

    override fun getItemCount(): Int = metrics.size

    fun updateMetrics(newMetrics: List<String>) {
        metrics = newMetrics
        notifyDataSetChanged()
    }
}
