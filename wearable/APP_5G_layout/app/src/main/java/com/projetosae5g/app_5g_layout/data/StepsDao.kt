package com.projetosae5g.app_5g_layout.data

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.Query

@Dao
interface StepsDao {
    @Query("SELECT * FROM steps")
    fun getAll(): List<StepCount>

    @Query("SELECT * FROM steps WHERE created_at >= date(:startDateTime) " +
            "AND created_at < date(:startDateTime, '+1 day')")
    fun loadAllStepsFromToday(startDateTime: String): List<StepCount>

    @Insert
    fun insertAll(vararg steps: StepCount): List<Long>

    @Delete
    fun delete(steps: StepCount): Int
} 