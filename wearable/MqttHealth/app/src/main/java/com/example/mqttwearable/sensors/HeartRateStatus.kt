package com.example.mqttwearable.sensors

object HeartRateStatus {
    const val HR_STATUS_NONE = 0
    const val HR_STATUS_FIND_HR = 1
    const val HR_STATUS_ATTACHED = -1
    const val HR_STATUS_DETECT_MOVE = -2
    const val HR_STATUS_DETACHED = -3
    const val HR_STATUS_LOW_RELIABILITY = -8
    const val HR_STATUS_VERY_LOW_RELIABILITY = -10
    const val HR_STATUS_NO_DATA_FLUSH = -99
} 