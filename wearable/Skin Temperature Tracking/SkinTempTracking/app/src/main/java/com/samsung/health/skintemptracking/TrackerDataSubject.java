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

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class TrackerDataSubject {

    private final List<TrackerObserver> trackerObservers = Collections.synchronizedList(new ArrayList<>());

    public void addObserver(TrackerObserver observer) {
        trackerObservers.add(observer);
    }

    public void removeObserver(TrackerObserver observer) {
        trackerObservers.remove(observer);
    }

    public void notifySkinTemperatureTrackerObservers(int status, float ambientTemperature, float wristSkinTemperature) {
        trackerObservers.forEach(observer -> observer.onSkinTemperatureChanged(status, ambientTemperature, wristSkinTemperature));
    }

    public void notifyError(int errorResourceId) {
        trackerObservers.forEach(observer -> observer.notifyTrackerError(errorResourceId));
    }
}
