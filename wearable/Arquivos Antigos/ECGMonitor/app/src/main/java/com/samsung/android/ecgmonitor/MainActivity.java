/*
 * Copyright 2023 Samsung Electronics Co., Ltd. All Rights Reserved.
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
package com.samsung.android.ecgmonitor;

import static android.content.pm.PackageManager.PERMISSION_DENIED;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.os.CountDownTimer;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.core.app.ActivityCompat;

import com.samsung.android.ecgmonitor.databinding.ActivityMainBinding;
import com.samsung.android.service.health.tracking.ConnectionListener;
import com.samsung.android.service.health.tracking.HealthTracker;
import com.samsung.android.service.health.tracking.HealthTrackerException;
import com.samsung.android.service.health.tracking.HealthTrackingService;
import com.samsung.android.service.health.tracking.data.DataPoint;
import com.samsung.android.service.health.tracking.data.HealthTrackerType;
import com.samsung.android.service.health.tracking.data.ValueKey;

import java.util.List;
import java.util.Locale;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

public class MainActivity extends Activity {

    private final String APP_TAG = "ECG Monitor";
    private final Handler ecgHandler = new Handler(Looper.getMainLooper());
    private final AtomicBoolean isMeasurementRunning = new AtomicBoolean(false);
    private final AtomicReference<Float> avgEcg = new AtomicReference<>();
    private final int MEASUREMENT_DURATION = 30000;
    private final int MEASUREMENT_TICK = 1000;
    private final AtomicBoolean leadOff = new AtomicBoolean(true);
    private final HealthTracker.TrackerEventListener ecgListener = new HealthTracker.TrackerEventListener() {
        @Override
        public void onDataReceived(@NonNull List<DataPoint> list) {
            if (list.size() == 0)
                return;
            final int isLeadOff = list.get(0).getValue(ValueKey.EcgSet.LEAD_OFF);
            final int NO_CONTACT = 5;
            if (isLeadOff == NO_CONTACT) {
                leadOff.set(true);
                return;
            } else
                leadOff.set(false);
            float sum = 0;
            for (DataPoint data : list) {
                final float curEcg = data.getValue(ValueKey.EcgSet.ECG_MV);
                sum += curEcg;
            }
            avgEcg.set(sum / list.size());
        }

        @Override
        public void onFlushCompleted() {
            Log.i(APP_TAG, " onFlushCompleted called");
        }

        @Override
        public void onError(HealthTracker.TrackerError trackerError) {
            Log.i(APP_TAG, " onError called");
            if (trackerError == HealthTracker.TrackerError.PERMISSION_ERROR) {
                runOnUiThread(() -> Toast.makeText(getApplicationContext(),
                        getString(R.string.NoPermission), Toast.LENGTH_SHORT).show());
            }
            if (trackerError == HealthTracker.TrackerError.SDK_POLICY_ERROR) {
                runOnUiThread(() -> Toast.makeText(getApplicationContext(),
                        getString(R.string.SDKPolicyError), Toast.LENGTH_SHORT).show());
            }
        }
    };
    private boolean permissionGranted = false;
    private TextView mTextView;
    private Button mButMeasure;
    private ActivityMainBinding binding;
    private HealthTrackingService healthTrackingService = null;
    private HealthTracker ecgTracker = null;
    CountDownTimer countDownTimer = new CountDownTimer(MEASUREMENT_DURATION, MEASUREMENT_TICK) {
        @Override
        public void onTick(long timeLeft) {
            if (timeLeft > MEASUREMENT_DURATION - 2000)
                return;
            if (isMeasurementRunning.get()) {
                if (leadOff.get()) {
                    runOnUiThread(() -> binding.txtOutput.setText(R.string.outputWarning));
                } else {
                    final String measureValue = getString(R.string.MeasurementUpdate, timeLeft / 1000, String.format(Locale.ENGLISH, "%.2f", avgEcg.get()));
                    runOnUiThread(() -> binding.txtOutput.setText(measureValue));
                }
            }
        }

        @Override
        public void onFinish() {
            ecgTracker.unsetEventListener();
            isMeasurementRunning.set(false);
            runOnUiThread(() ->
            {
                getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                if (leadOff.get())
                    binding.txtOutput.setText(R.string.MeasurementFailed);
                else {
                    final String finalEcgStr = getString(R.string.MeasurementSuccessful, String.format(Locale.ENGLISH, "%.2f", avgEcg.get()));
                    binding.txtOutput.setText(finalEcgStr);
                }
                binding.butStart.setText(R.string.RepeatMeasurement);
            });
        }
    };
    private boolean connected = false;
    private final ConnectionListener connectionListener = new ConnectionListener() {
        @Override
        public void onConnectionSuccess() {
            Log.i(APP_TAG, "Connected");
            Toast.makeText(getApplicationContext(), getString(R.string.ConnectedToHS), Toast.LENGTH_SHORT).show();
            checkCapabilities();
            connected = true;
            ecgTracker = healthTrackingService.getHealthTracker(HealthTrackerType.ECG_ON_DEMAND);
        }

        @Override
        public void onConnectionEnded() {
            Log.i(APP_TAG, "Disconnected");
        }

        @Override
        public void onConnectionFailed(HealthTrackerException e) {
            if (e.getErrorCode() == HealthTrackerException.OLD_PLATFORM_VERSION || e.getErrorCode() == HealthTrackerException.PACKAGE_NOT_INSTALLED)
                Toast.makeText(getApplicationContext(), getString(R.string.NoHealthPlatformError), Toast.LENGTH_LONG).show();
            if (e.hasResolution()) {
                e.resolve(MainActivity.this);
            } else {
                Log.e(APP_TAG, "Could not connect to Health Services: " + e.getMessage());
                runOnUiThread(() -> Toast.makeText(getApplicationContext(), getString(R.string.ConnectionError), Toast.LENGTH_LONG).show());
            }
            finish();
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        binding = ActivityMainBinding.inflate(getLayoutInflater());
        setContentView(binding.getRoot());

        mTextView = binding.txtOutput;
        mButMeasure = binding.butStart;
        mButMeasure.setOnClickListener(unused -> startMeasurement());

        if (ActivityCompat.checkSelfPermission(getApplicationContext(), "android.permission.BODY_SENSORS") == PackageManager.PERMISSION_DENIED)
            requestPermissions(new String[]{Manifest.permission.BODY_SENSORS}, 0);
        else
            permissionGranted = true;
        try {
            healthTrackingService = new HealthTrackingService(connectionListener, getApplicationContext());
            healthTrackingService.connectService();
        } catch (Throwable t) {
            final String msg = t.getMessage();
            Log.e(APP_TAG, msg == null ? "" : msg);
        }
    }


    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (ecgTracker != null)
            ecgTracker.unsetEventListener();
        isMeasurementRunning.set(false);
        ecgHandler.removeCallbacksAndMessages(null);
        if (healthTrackingService != null)
            healthTrackingService.disconnectService();
    }

    private void checkCapabilities() {
        final List<HealthTrackerType> availableTrackers = healthTrackingService.getTrackingCapability().getSupportHealthTrackerTypes();
        if (!availableTrackers.contains(HealthTrackerType.ECG_ON_DEMAND)) {
            Toast.makeText(getApplicationContext(), getString(R.string.NoECGSupport), Toast.LENGTH_LONG).show();
            Log.e(APP_TAG, "Device does not support ECG tracking");
            finish();
        }
    }

    private void startMeasurement() {
        if (ActivityCompat.checkSelfPermission(getApplicationContext(), "android.permission.BODY_SENSORS") == PackageManager.PERMISSION_DENIED)
            requestPermissions(new String[]{Manifest.permission.BODY_SENSORS}, 0);
        if (!permissionGranted) {
            Log.i(APP_TAG, "Could not get permissions. Terminating measurement");
            return;
        }
        if (!connected) {
            Toast.makeText(getApplicationContext(), getString(R.string.ConnectionError), Toast.LENGTH_SHORT).show();
            return;
        }
        if (!isMeasurementRunning.get()) {
            mTextView.setText(R.string.outputMeasuring);
            mButMeasure.setText(R.string.stop);
            isMeasurementRunning.set(true);
            getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
            ecgHandler.post(() -> ecgTracker.setEventListener(ecgListener));
            final Thread uiUpdateThread = new Thread(() -> countDownTimer.start());
            uiUpdateThread.start();
        } else {
            if (ecgTracker != null)
                ecgTracker.unsetEventListener();
            ecgHandler.removeCallbacksAndMessages(null);
            isMeasurementRunning.set(false);
            mButMeasure.setText(R.string.start);
            mTextView.setText(R.string.outputStart);
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, @NonNull int[] grantResults) {
        if (requestCode == 0) {
            permissionGranted = true;
            for (int i = 0; i < permissions.length; ++i) {
                if (grantResults[i] == PERMISSION_DENIED) {
                    //User denied permissions twice - permanent denial:
                    if (!shouldShowRequestPermissionRationale(permissions[i])) {
                        Toast.makeText(getApplicationContext(), getString(R.string.PermissionDeniedPermanently), Toast.LENGTH_LONG).show();
                    }
                    //User denied permissions once:
                    else {
                        Toast.makeText(getApplicationContext(), getString(R.string.PermissionDeniedRationale), Toast.LENGTH_LONG).show();
                    }
                    permissionGranted = false;
                    break;
                }
            }
        }
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
    }
}