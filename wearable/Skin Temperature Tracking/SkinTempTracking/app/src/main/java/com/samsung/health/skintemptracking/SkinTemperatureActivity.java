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

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Settings;
import android.util.Log;
import android.view.View;
import android.widget.Toast;

import androidx.core.app.ActivityCompat;

import com.samsung.health.skintemptracking.databinding.ActivitySkintemperatureBinding;

import java.util.Locale;
import java.util.concurrent.atomic.AtomicBoolean;

public class SkinTemperatureActivity extends Activity implements TrackerObserver {
    private final String APP_TAG = "SkinTemperature";
    private final AtomicBoolean connected = new AtomicBoolean(false);
    private TrackerDataSubject trackerDataSubject = null;
    private boolean skinTemperatureAvailable = false;
    private SkinTemperatureListener skinTemperatureListener = null;
    private ConnectionManager connectionManager = null;
    private final ConnectionObserver connectionObserver = new ConnectionObserver() {
        @Override
        public void onConnectionResult(int stringResourceId) {
            runOnUiThread(() ->
                    Toast.makeText(getApplicationContext(), getString(stringResourceId), Toast.LENGTH_LONG).show());
            connected.set(stringResourceId == R.string.connected_to_health_services);
        }

        @Override
        public void onSkinTemperatureAvailability(boolean isAvailable) {
            skinTemperatureAvailable = isAvailable;
            if (isAvailable) {
                skinTemperatureListener = new SkinTemperatureListener();
                skinTemperatureListener.setTrackerDataSubject(trackerDataSubject);
                connectionManager.initSkinTemperature(skinTemperatureListener);
            }
        }
    };
    private ActivitySkintemperatureBinding activitySkintemperatureBinding = null;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        activitySkintemperatureBinding = ActivitySkintemperatureBinding.inflate(getLayoutInflater());
        setContentView(activitySkintemperatureBinding.getRoot());

        if (ActivityCompat.checkSelfPermission(getApplicationContext(), getString(R.string.body_sensors)) == PackageManager.PERMISSION_DENIED)
            requestPermissions(new String[]{Manifest.permission.BODY_SENSORS}, 0);
        trackerDataSubject = new TrackerDataSubject();
        trackerDataSubject.addObserver(this);
        createConnectionManager();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (skinTemperatureListener != null)
            skinTemperatureListener.stopTracker();
        trackerDataSubject.removeObserver(this);
        if (connectionManager != null) {
            connectionManager.disconnect();
        }
    }

    void createConnectionManager() {
        try {
            connectionManager = new ConnectionManager(connectionObserver);
            connectionManager.connect(this, getApplicationContext());
        } catch (Throwable t) {
            final String errMsg = t.getMessage() == null ? "Error in creating connection manager" : t.getMessage();
            Log.e(APP_TAG, errMsg);
        }
    }

    public void startMeasurement(View view) {
        if (!connected.get()) {
            prepareAlertWindow(R.string.no_connection_title, R.string.no_connection_message).create().show();
            return;
        }
        if (!skinTemperatureAvailable) {
            prepareAlertWindow(R.string.no_skin_temperature_available_title, R.string.no_skin_temperature_available_message).create().show();
            return;
        }
        activitySkintemperatureBinding.txtStatus.setText(R.string.header_label_measuring);
        activitySkintemperatureBinding.butStart.setText(R.string.button_measuring);
        activitySkintemperatureBinding.txtAmbientTemperatureValue.setText(R.string.ambient_temperature_default_value);
        activitySkintemperatureBinding.txtWristSkinTemperatureValue.setText(R.string.wrist_skin_temperature_default_value);
        activitySkintemperatureBinding.pgMeasurement.setVisibility(View.VISIBLE);
        activitySkintemperatureBinding.butStart.setEnabled(false);
        skinTemperatureListener.startTracker();
    }

    @Override
    public void onSkinTemperatureChanged(int status, float ambientTemperature, float wristSkinTemperature) {
        endMeasurement();
        if (status == SkinTemperatureStatus.INVALID_MEASUREMENT) {
            Log.i(APP_TAG, "Invalid skin temperature measurement");
            return;
        }
        runOnUiThread(() -> {
            activitySkintemperatureBinding.txtAmbientTemperatureValue.setText(
                    String.format(Locale.getDefault(), "%.1f", ambientTemperature));
            activitySkintemperatureBinding.txtWristSkinTemperatureValue.setText(
                    String.format(Locale.getDefault(), "%.1f", wristSkinTemperature));
        });
        Log.i(APP_TAG, "Measurement done");
    }

    void endMeasurement() {
        skinTemperatureListener.stopTracker();
        runOnUiThread(() -> {
            activitySkintemperatureBinding.txtStatus.setText(R.string.header_label_measurement_done);
            activitySkintemperatureBinding.butStart.setText(R.string.button_default_value);
            activitySkintemperatureBinding.pgMeasurement.setVisibility(View.INVISIBLE);
            activitySkintemperatureBinding.butStart.setEnabled(true);
        });
    }

    @Override
    public void notifyTrackerError(int errorResourceId) {
        endMeasurement();
        runOnUiThread(() -> {
            if (errorResourceId == R.string.no_permission_message) {
                final AlertDialog.Builder alertBuilder = prepareAlertWindow(R.string.no_permission_title, R.string.no_permission_message);
                alertBuilder.setPositiveButton("Settings", (dialog, which) -> openAppSettings(getPackageName()));
                alertBuilder.setNegativeButton("Not now", null);
                final AlertDialog alertDialog = alertBuilder.create();
                alertDialog.show();
            }
            if (errorResourceId == R.string.sdk_policy_error_message) {
                prepareAlertWindow(R.string.sdk_policy_error_title, R.string.sdk_policy_error_message).create().show();
            }
        });
    }


    void openAppSettings(String packageName) {
        final Intent intent = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
        final Uri uri = Uri.fromParts("package", packageName, null);
        intent.setData(uri);
        startActivity(intent);
    }

    AlertDialog.Builder prepareAlertWindow(int titleResourceId, int messageResourceId) {
        final AlertDialog.Builder alertBuilder = new AlertDialog.Builder(this);
        alertBuilder.setMessage(messageResourceId);
        alertBuilder.setTitle(titleResourceId);
        return alertBuilder;
    }
}
