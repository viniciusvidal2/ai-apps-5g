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

import java.util.List;

public class PpgData {
    public List<Integer> ppgGreen;
    public List<Integer> ppgIr;
    public List<Integer> ppgRed;
    public long timestamp;
    public int status;

    public PpgData() {
        this.ppgGreen = null;
        this.ppgIr = null;
        this.ppgRed = null;
        this.timestamp = 0;
        this.status = 0;
    }

    public PpgData(List<Integer> ppgGreen, List<Integer> ppgIr, List<Integer> ppgRed, long timestamp, int status) {
        this.ppgGreen = ppgGreen;
        this.ppgIr = ppgIr;
        this.ppgRed = ppgRed;
        this.timestamp = timestamp;
        this.status = status;
    }

    @Override
    public String toString() {
        return "PpgData{" +
                "ppgGreen=" + (ppgGreen != null ? ppgGreen.size() : 0) + " values" +
                ", ppgIr=" + (ppgIr != null ? ppgIr.size() : 0) + " values" +
                ", ppgRed=" + (ppgRed != null ? ppgRed.size() : 0) + " values" +
                ", timestamp=" + timestamp +
                ", status=" + status +
                '}';
    }
} 