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

import android.app.Activity;
import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;

import com.samsung.android.service.health.tracking.ConnectionListener;
import com.samsung.android.service.health.tracking.HealthTrackerCapability;
import com.samsung.android.service.health.tracking.HealthTrackerException;
import com.samsung.android.service.health.tracking.HealthTrackingService;
import com.samsung.android.service.health.tracking.data.HealthTrackerType;

import java.util.List;

public class ConnectionManager {

    private final String TAG = "ConnectionManager";
    private final ConnectionObserver connectionObserver;
    private HealthTrackingService healthTrackingService = null;
    private Activity callingActivity = null;
    private final ConnectionListener connectionListener = new ConnectionListener() {
        @Override
        public void onConnectionSuccess() {
            Log.i(TAG, "Connected");
            connectionObserver.onConnectionResult(R.string.connected_to_health_services);
            final boolean availability = isSkinTemperatureAvailable(healthTrackingService);
            connectionObserver.onSkinTemperatureAvailability(availability);
        }

        @Override
        public void onConnectionEnded() {
            Log.i(TAG, "Disconnected");
        }

        @Override
        public void onConnectionFailed(HealthTrackerException e) {
            if (e.hasResolution())
                e.resolve(callingActivity);
            connectionObserver.onConnectionResult(R.string.no_valid_health_platform);
            final String errMsg = e.getMessage() == null ? "" : e.getMessage();
            Log.i(TAG, "Could not connect to Health Tracking Service: " + errMsg);
        }
    };

    ConnectionManager(ConnectionObserver connectionObserver) {
        this.connectionObserver = connectionObserver;
    }

    void connect(Activity activity, Context context) {
        callingActivity = activity;
        healthTrackingService = new HealthTrackingService(connectionListener, context);
        healthTrackingService.connectService();
    }

    void disconnect() {
        if (healthTrackingService != null)
            healthTrackingService.disconnectService();
    }

    boolean isSkinTemperatureAvailable(HealthTrackingService healthTrackingService) {
        if (healthTrackingService == null)
            return false;
        @SuppressWarnings("UnusedAssignment") List<HealthTrackerType> availableTrackers = null;
        availableTrackers = checkAvailableTrackers(healthTrackingService.getTrackingCapability());
        if (availableTrackers == null)
            return false;
        else
            return availableTrackers.contains(HealthTrackerType.SKIN_TEMPERATURE_ON_DEMAND);
    }

    List<HealthTrackerType> checkAvailableTrackers(HealthTrackerCapability healthTrackerCapability) {
        if (healthTrackerCapability == null)
            return null;
        return healthTrackerCapability.getSupportHealthTrackerTypes();
    }

    void initSkinTemperature(SkinTemperatureListener skinTemperatureListener) {
        skinTemperatureListener.setSkinTemperatureTracker(healthTrackingService);
        skinTemperatureListener.setSkinTemperatureHandler(new Handler(Looper.getMainLooper()));
    }
}
