/*
 * Copyright 2024 Samsung Electronics Co., Ltd. All Rights Reserved.
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

package com.samsung.health.multisensortracking;

import android.util.Log;

import com.samsung.android.service.health.tracking.HealthTracker;
import com.samsung.android.service.health.tracking.data.DataPoint;
import com.samsung.android.service.health.tracking.data.ValueKey;

import java.util.List;

public class PpgListener extends BaseListener {

    private final static String APP_TAG = "PpgListener";

    private final HealthTracker.TrackerEventListener trackerEventListener = new HealthTracker.TrackerEventListener() {
        @Override
        public void onDataReceived(List<DataPoint> dataPoints) {
            for (DataPoint dataPoint : dataPoints) {
                readValuesFromDataPoint(dataPoint);
            }
        }

        @Override
        public void onFlushCompleted() {
            Log.i(APP_TAG, "onFlushCompleted called");
        }

        @Override
        public void onError(HealthTracker.TrackerError trackerError) {
            Log.e(APP_TAG, "onError called: " + trackerError);
            setHandlerRunning(false);
            if (trackerError == HealthTracker.TrackerError.PERMISSION_ERROR) {
                TrackerDataNotifier.getInstance().notifyError(R.string.NoPermission);
            } else {
                TrackerDataNotifier.getInstance().notifyError(R.string.SdkPolicyError);
            }
        }
    };

    public PpgListener() {
        super.setTrackerEventListener(trackerEventListener);
    }

    private List<Integer> convertToList(Object value) {
        List<Integer> result = new java.util.ArrayList<>();
        if (value instanceof List) {
            try {
                @SuppressWarnings("unchecked")
                List<Integer> list = (List<Integer>) value;
                result = list;
            } catch (ClassCastException e) {
                Log.w(APP_TAG, "Could not cast to List<Integer>: " + e.getMessage());
            }
        } else if (value instanceof Integer) {
            result.add((Integer) value);
        } else if (value != null) {
            Log.w(APP_TAG, "Unexpected PPG value type: " + value.getClass().getSimpleName());
        }
        return result;
    }

    private void readValuesFromDataPoint(DataPoint dataPoint) {
        try {
            List<Integer> ppgGreenList = null;
            List<Integer> ppgIrList = null;
            List<Integer> ppgRedList = null;
            final long timestamp = dataPoint.getTimestamp();
            int status = 0;

            // Tentar usar ValueKey.PpgSet primeiro (versão mais nova)
            try {
                // Os dados PPG podem vir como Integer ou List<Integer> dependendo da versão
                Object greenValue = dataPoint.getValue(ValueKey.PpgSet.PPG_GREEN);
                Object irValue = dataPoint.getValue(ValueKey.PpgSet.PPG_IR);
                Object redValue = dataPoint.getValue(ValueKey.PpgSet.PPG_RED);
                
                ppgGreenList = convertToList(greenValue);
                ppgIrList = convertToList(irValue);
                ppgRedList = convertToList(redValue);
                Log.i(APP_TAG, "Using new PpgSet API");
            } catch (Exception e) {
                // Fallback para API antiga se disponível
                try {
                    // Tentar usar ValueKey.PpgGreenSet (API depreciada mas ainda funcional)
                    Object greenValue = dataPoint.getValue(ValueKey.PpgGreenSet.PPG_GREEN);
                    ppgGreenList = convertToList(greenValue);
                    status = (Integer) dataPoint.getValue(ValueKey.PpgGreenSet.STATUS);
                    Log.i(APP_TAG, "Using deprecated PpgGreenSet API");
                } catch (Exception e2) {
                    Log.w(APP_TAG, "Could not read PPG data with either API: " + e2.getMessage());
                    // Criar listas vazias como fallback
                    ppgGreenList = new java.util.ArrayList<>();
                    ppgIrList = new java.util.ArrayList<>();
                    ppgRedList = new java.util.ArrayList<>();
                }
            }

            final PpgData ppgData = new PpgData(ppgGreenList, ppgIrList, ppgRedList, timestamp, status);
            
            Log.i(APP_TAG, "PPG Data received: " + ppgData.toString());
            TrackerDataNotifier.getInstance().notifyPpgTrackerObservers(ppgData);
        } catch (Exception e) {
            Log.e(APP_TAG, "Error reading PPG data: " + e.getMessage());
            // Criar dados vazios em caso de erro
            final PpgData ppgData = new PpgData();
            ppgData.timestamp = dataPoint.getTimestamp();
            TrackerDataNotifier.getInstance().notifyPpgTrackerObservers(ppgData);
        }
    }
} 