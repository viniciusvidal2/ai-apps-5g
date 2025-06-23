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

import static org.junit.Assert.assertEquals;
import static org.mockito.ArgumentMatchers.anyFloat;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.verify;

import com.samsung.android.service.health.tracking.HealthTrackingService;
import com.samsung.android.service.health.tracking.data.DataPoint;
import com.samsung.android.service.health.tracking.data.HealthTrackerType;
import com.samsung.android.service.health.tracking.data.Value;
import com.samsung.android.service.health.tracking.data.ValueKey;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.MockitoJUnitRunner;

import java.util.HashMap;
import java.util.Map;

@RunWith(MockitoJUnitRunner.class)
public class SkinTemperatureListenerTest {
    private final float AMBIENT_TEMPERATURE = 30;
    private final float WRIST_SKIN_TEMPERATURE = 32;
    private final double DELTA = 0.01;
    private final int STATUS = SkinTemperatureStatus.SUCCESSFUL_MEASUREMENT;
    @Mock
    TrackerObserver trackerObserver;
    @InjectMocks
    TrackerDataSubject trackerDataSubject;
    @Mock
    HealthTrackingService healthTrackingService;
    @InjectMocks
    SkinTemperatureListener skinTemperatureListener;

    @Test
    public void shouldUpdateSkinTemperatureValuesFromDataPoint_P() {
        @SuppressWarnings("rawtypes") final Map<ValueKey, Value> values = new HashMap<>();
        values.put(ValueKey.SkinTemperatureSet.STATUS, new Value<>(STATUS));
        values.put(ValueKey.SkinTemperatureSet.AMBIENT_TEMPERATURE, new Value<>(AMBIENT_TEMPERATURE));
        values.put(ValueKey.SkinTemperatureSet.OBJECT_TEMPERATURE, new Value<>(WRIST_SKIN_TEMPERATURE));
        final DataPoint dataPoint = new DataPoint(values);

        //when
        doAnswer(invocation -> {
            final int arg0 = invocation.getArgument(0);
            final float arg1 = invocation.getArgument(1);
            final float arg2 = invocation.getArgument(2);

            assertEquals(STATUS, arg0);
            assertEquals(AMBIENT_TEMPERATURE, arg1, DELTA);
            assertEquals(WRIST_SKIN_TEMPERATURE, arg2, DELTA);
            return null;
        }).when(trackerObserver).onSkinTemperatureChanged(anyInt(), anyFloat(), anyFloat());

        trackerDataSubject.addObserver(trackerObserver);
        skinTemperatureListener.setTrackerDataSubject(trackerDataSubject);

        skinTemperatureListener.updateSkinTemperature(dataPoint);

        //then
        trackerDataSubject.removeObserver(trackerObserver);
    }

    @Test
    public void shouldInitSkinTemperature_P() {
        //given
        skinTemperatureListener.setSkinTemperatureTracker(healthTrackingService);

        //then
        verify(healthTrackingService).getHealthTracker(HealthTrackerType.SKIN_TEMPERATURE_ON_DEMAND);
    }

}
