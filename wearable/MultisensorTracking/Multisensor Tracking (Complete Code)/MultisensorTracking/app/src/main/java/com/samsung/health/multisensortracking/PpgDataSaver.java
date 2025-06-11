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

import android.content.Context;
import android.util.Log;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

public class PpgDataSaver {
    private static final String APP_TAG = "PpgDataSaver";
    private final List<PpgData> ppgDataList;
    private final Context context;

    public PpgDataSaver(Context context) {
        this.context = context;
        this.ppgDataList = new ArrayList<>();
    }

    public void addPpgData(PpgData ppgData) {
        ppgDataList.add(ppgData);
        Log.i(APP_TAG, "PPG data added. Total samples: " + ppgDataList.size());
    }

    public String saveToFile() {
        if (ppgDataList.isEmpty()) {
            Log.w(APP_TAG, "No PPG data to save");
            return null;
        }

        try {
            // Criar nome do arquivo com timestamp
            SimpleDateFormat sdf = new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault());
            String timestamp = sdf.format(new Date());
            String fileName = "ppg_data_" + timestamp + ".csv";

            // Obter diretório de arquivos da aplicação
            File filesDir = context.getFilesDir();
            File ppgFile = new File(filesDir, fileName);

            FileWriter writer = new FileWriter(ppgFile);

            // Escrever cabeçalho CSV
            writer.append("Timestamp,Status,PPG_Green,PPG_IR,PPG_Red\n");

            // Escrever dados
            for (PpgData data : ppgDataList) {
                if (data.ppgGreen != null && data.ppgIr != null && data.ppgRed != null) {
                    int maxSize = Math.max(Math.max(data.ppgGreen.size(), data.ppgIr.size()), data.ppgRed.size());
                    
                    for (int i = 0; i < maxSize; i++) {
                        writer.append(String.valueOf(data.timestamp)).append(",");
                        writer.append(String.valueOf(data.status)).append(",");
                        
                        // PPG Green
                        if (i < data.ppgGreen.size()) {
                            writer.append(String.valueOf(data.ppgGreen.get(i)));
                        } else {
                            writer.append("0");
                        }
                        writer.append(",");
                        
                        // PPG IR
                        if (i < data.ppgIr.size()) {
                            writer.append(String.valueOf(data.ppgIr.get(i)));
                        } else {
                            writer.append("0");
                        }
                        writer.append(",");
                        
                        // PPG Red
                        if (i < data.ppgRed.size()) {
                            writer.append(String.valueOf(data.ppgRed.get(i)));
                        } else {
                            writer.append("0");
                        }
                        writer.append("\n");
                    }
                }
            }

            writer.close();
            
            String filePath = ppgFile.getAbsolutePath();
            Log.i(APP_TAG, "PPG data saved to: " + filePath);
            Log.i(APP_TAG, "Total data points saved: " + ppgDataList.size());
            
            // Limpar dados após salvar
            ppgDataList.clear();
            
            return filePath;

        } catch (IOException e) {
            Log.e(APP_TAG, "Error saving PPG data: " + e.getMessage());
            return null;
        }
    }

    public int getDataCount() {
        return ppgDataList.size();
    }

    public void clearData() {
        ppgDataList.clear();
        Log.i(APP_TAG, "PPG data cleared");
    }
} 