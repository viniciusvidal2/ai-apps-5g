/*
 * Copyright 2022 Samsung Electronics Co., Ltd. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.samsung.health.skintemptracking;

import android.os.Handler;
import android.util.Log;

import androidx.annotation.NonNull;

import com.samsung.android.service.health.tracking.HealthTracker;
import com.samsung.android.service.health.tracking.HealthTrackingService;
import com.samsung.android.service.health.tracking.data.DataPoint;
import com.samsung.android.service.health.tracking.data.HealthTrackerType;
import com.samsung.android.service.health.tracking.data.ValueKey;

import java.util.List;

public class SkinTemperatureListener {
    private final String TAG = "SkinTemperatureListener";
    private TrackerDataSubject trackerDataSubject;
    private final HealthTracker.TrackerEventListener skinTemperatureListener = new HealthTracker.TrackerEventListener() {
        @Override
        public void onDataReceived(@NonNull List<DataPoint> list) {
            for (DataPoint data : list) {
                updateSkinTemperature(data);
            }
        }

        @Override
        public void onFlushCompleted() {
            Log.i(TAG, "Flush completed");
        }

        @Override
        public void onError(HealthTracker.TrackerError trackerError) {
            Log.i(TAG, "Skin Temperature Tracker error: " + trackerError.toString());
            if (trackerError == HealthTracker.TrackerError.PERMISSION_ERROR) {
                trackerDataSubject.notifyError(R.string.no_permission_message);
            }
            if (trackerError == HealthTracker.TrackerError.SDK_POLICY_ERROR) {
                trackerDataSubject.notifyError(R.string.sdk_policy_error_message);
            }
        }
    };
    private Handler skinTemperatureHandler;
    private boolean isHandlerRunning = false;
    private HealthTracker skinTemperatureTracker;

    void setTrackerDataSubject(TrackerDataSubject trackerDataSubject) {
        this.trackerDataSubject = trackerDataSubject;
    }

    void setSkinTemperatureTracker(HealthTrackingService healthTrackingService) {
        skinTemperatureTracker = healthTrackingService.getHealthTracker(HealthTrackerType.SKIN_TEMPERATURE_ON_DEMAND);
    }

    void setSkinTemperatureHandler(Handler handler) {
        skinTemperatureHandler = handler;
    }

    void startTracker() {
        if (!isHandlerRunning) {
            skinTemperatureHandler.post(() -> skinTemperatureTracker.setEventListener(skinTemperatureListener));
            isHandlerRunning = true;
        }
    }

    void stopTracker() {
        if (skinTemperatureTracker != null)
            skinTemperatureTracker.unsetEventListener();
        skinTemperatureHandler.removeCallbacksAndMessages(null);
        isHandlerRunning = false;
    }

    void updateSkinTemperature(DataPoint data) {
        final int status = data.getValue(ValueKey.SkinTemperatureSet.STATUS);
        float wristSkinTemperatureValue = 0;
        float ambientTemperatureValue = 0;
        if (status == SkinTemperatureStatus.SUCCESSFUL_MEASUREMENT) {
            wristSkinTemperatureValue = data.getValue(ValueKey.SkinTemperatureSet.OBJECT_TEMPERATURE);
            ambientTemperatureValue = data.getValue(ValueKey.SkinTemperatureSet.AMBIENT_TEMPERATURE);
        }
        trackerDataSubject.notifySkinTemperatureTrackerObservers(status, ambientTemperatureValue, wristSkinTemperatureValue);
    }
}
