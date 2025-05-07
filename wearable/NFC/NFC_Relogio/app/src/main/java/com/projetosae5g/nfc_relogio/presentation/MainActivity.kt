/* While this template provides a good starting point for using Wear Compose, you can always
 * take a look at https://github.com/android/wear-os-samples/tree/main/ComposeStarter and
 * https://github.com/android/wear-os-samples/tree/main/ComposeAdvanced to find the most up to date
 * changes to the libraries and their usages.
 */

package com.projetosae5g.nfc_relogio.presentation

import android.app.PendingIntent
import android.content.Intent
import android.nfc.NdefMessage
import android.nfc.NdefRecord
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.nfc.tech.Ndef
import android.nfc.tech.NdefFormatable
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Devices
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.wear.compose.material.Button
import androidx.wear.compose.material.MaterialTheme
import androidx.wear.compose.material.Text
import androidx.wear.compose.material.TimeText
import com.projetosae5g.nfc_relogio.R
import com.projetosae5g.nfc_relogio.presentation.theme.NFC_RelogioTheme
import kotlin.random.Random

/**
 * Aplicativo para o Samsung Watch 7 (Wear OS) que gera códigos aleatórios de 6 dígitos
 * e os envia via NFC para um smartphone Android.
 * 
 * Esta versão usa a abordagem mais básica e amplamente compatível do NFC.
 */
class MainActivity : ComponentActivity(), NfcAdapter.ReaderCallback {
    private var nfcAdapter: NfcAdapter? = null
    private val randomCode = mutableStateOf(generateRandomCode())
    private val TAG = "NFC_RELOGIO"
    private lateinit var pendingIntent: PendingIntent
    
    // Estatísticas para melhorar a depuração
    companion object {
        var currentCode = ""
        var tagCount = 0
        var lastTagId = ""
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        setTheme(android.R.style.Theme_DeviceDefault)
        
        try {
            // Inicializa o adaptador NFC
            nfcAdapter = NfcAdapter.getDefaultAdapter(this)
            
            if (nfcAdapter == null) {
                Toast.makeText(this, "Este dispositivo não suporta NFC", Toast.LENGTH_LONG).show()
                Log.e(TAG, "NFC não suportado neste dispositivo")
            } else {
                // Atualiza o código atual
                updateCurrentCode()
                Log.d(TAG, "NFC disponível no dispositivo")
                
                // Configura o PendingIntent para o foreground dispatch
                val intent = Intent(this, javaClass).apply {
                    addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
                }
                pendingIntent = PendingIntent.getActivity(
                    this, 0, intent, PendingIntent.FLAG_MUTABLE
                )
                
                Toast.makeText(this, "NFC pronto para enviar: ${randomCode.value}", Toast.LENGTH_SHORT).show()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Erro ao inicializar NFC: ${e.message}")
            Toast.makeText(this, "Erro NFC: ${e.message}", Toast.LENGTH_LONG).show()
        }
        
        setContent {
            WearApp(
                code = randomCode.value, 
                tagCount = tagCount,
                onGenerateNewCode = {
                    randomCode.value = generateRandomCode()
                    updateCurrentCode()
                    Toast.makeText(this, "Novo código gerado: ${randomCode.value}", Toast.LENGTH_SHORT).show()
                    Log.d(TAG, "Novo código gerado: ${randomCode.value}")
                }
            )
        }
    }
    
    // Atualiza o código atual no companion object
    private fun updateCurrentCode() {
        currentCode = randomCode.value
    }
    
    // Gera um código aleatório de 6 caracteres
    private fun generateRandomCode(): String {
        // Gera apenas dígitos numéricos (0-9)
        val chars = "0123456789"
        return (1..6).map { chars[Random.nextInt(chars.length)] }.joinToString("")
    }
    
    override fun onResume() {
        super.onResume()
        try {
            // Habilita o modo de leitura NFC - isto permite que o relógio detecte
            // e interaja com tags NFC próximas, como celulares
            nfcAdapter?.enableReaderMode(this, this,
                NfcAdapter.FLAG_READER_NFC_A or
                NfcAdapter.FLAG_READER_NFC_B or
                NfcAdapter.FLAG_READER_NFC_F or
                NfcAdapter.FLAG_READER_NFC_V or
                NfcAdapter.FLAG_READER_NO_PLATFORM_SOUNDS,
                null)
            
            Log.d(TAG, "Modo de leitura NFC habilitado")
        } catch (e: Exception) {
            Log.e(TAG, "Erro ao habilitar NFC: ${e.message}")
            Toast.makeText(this, "Erro ao ativar NFC: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }
    
    override fun onPause() {
        super.onPause()
        try {
            // Desabilita o modo de leitura NFC
            nfcAdapter?.disableReaderMode(this)
            Log.d(TAG, "Modo de leitura NFC desabilitado")
        } catch (e: Exception) {
            Log.e(TAG, "Erro ao desabilitar NFC: ${e.message}")
        }
    }
    
    // Callback para quando uma tag NFC for detectada
    override fun onTagDiscovered(tag: Tag?) {
        if (tag == null) {
            Log.e(TAG, "Tag NFC nula detectada")
            return
        }
        
        val tagId = tag.id.joinToString(":") { "%02X".format(it) }
        lastTagId = tagId
        tagCount++
        
        Log.d(TAG, "Tag NFC detectada #$tagCount com ID: $tagId")
        
        try {
            // Tenta escrever o código atual na tag
            val success = writeNdefMessage(tag, currentCode)
            
            if (success) {
                Log.d(TAG, "Código enviado com sucesso: $currentCode")
                runOnUiThread {
                    Toast.makeText(this, "Código $currentCode enviado", Toast.LENGTH_SHORT).show()
                }
            } else {
                Log.e(TAG, "Falha ao enviar código")
                runOnUiThread {
                    Toast.makeText(this, "Falha ao enviar código", Toast.LENGTH_SHORT).show()
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Erro ao escrever na tag: ${e.message}")
            e.printStackTrace()
            runOnUiThread {
                Toast.makeText(this, "Erro NFC: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }
    
    // Função para escrever o código em uma tag NFC
    private fun writeNdefMessage(tag: Tag, message: String): Boolean {
        try {
            // Obtém o ID único do dispositivo relógio
            val deviceId = Build.MODEL.replace(" ", "_")
            
            // Cria a mensagem completa contendo ID, origem e código
            val fullMessage = "ID=$deviceId,ORIGEM=relogio,CODIGO=$message"
            Log.d(TAG, "Mensagem para envio: $fullMessage")
            
            // Cria diferentes tipos de registros NDEF para aumentar compatibilidade
            
            // 1. Registro de texto padrão
            val textRecord = NdefRecord.createTextRecord("pt-BR", fullMessage)
            
            // 2. Registro MIME (mais compatível com alguns dispositivos)
            val mimeRecord = NdefRecord.createMime("text/plain", fullMessage.toByteArray())
            
            // 3. Registro URI - alternativa que alguns dispositivos reconhecem melhor
            val uriRecord = NdefRecord.createUri("https://example.com/nfc?data=$fullMessage")
            
            // Cria uma mensagem NDEF com todos os registros (maior chance de compatibilidade)
            val ndefMessage = NdefMessage(arrayOf(textRecord, mimeRecord, uriRecord))
            
            // Tenta escrever na tag
            val ndef = Ndef.get(tag)
            
            if (ndef != null) {
                try {
                    ndef.connect()
                    
                    // Verifica tamanho máximo e se a tag está protegida
                    val maxSize = ndef.maxSize
                    val messageSize = ndefMessage.toByteArray().size
                    
                    Log.d(TAG, "Tamanho da mensagem: $messageSize bytes, máximo da tag: $maxSize bytes")
                    
                    if (messageSize > maxSize) {
                        Log.e(TAG, "Mensagem muito grande para a tag (${messageSize}/${maxSize} bytes)")
                        runOnUiThread {
                            Toast.makeText(this, "Mensagem muito grande para tag", Toast.LENGTH_SHORT).show()
                        }
                        return false
                    }
                    
                    if (ndef.isWritable) {
                        ndef.writeNdefMessage(ndefMessage)
                        Log.d(TAG, "Mensagem NDEF escrita com sucesso")
                        return true
                    } else {
                        Log.e(TAG, "Tag não é gravável")
                        runOnUiThread {
                            Toast.makeText(this, "Tag não é gravável", Toast.LENGTH_SHORT).show()
                        }
                    }
                    
                    ndef.close()
                } catch (e: Exception) {
                    Log.e(TAG, "Erro ao escrever usando Ndef: ${e.message}")
                    e.printStackTrace()
                }
            } else {
                // Se a tag não for formatada em NDEF, tenta formatá-la
                val ndefFormatable = NdefFormatable.get(tag)
                if (ndefFormatable != null) {
                    try {
                        ndefFormatable.connect()
                        ndefFormatable.format(ndefMessage)
                        Log.d(TAG, "Tag formatada e escrita com sucesso")
                        ndefFormatable.close()
                        return true
                    } catch (e: Exception) {
                        Log.e(TAG, "Erro ao formatar tag: ${e.message}")
                        e.printStackTrace()
                    }
                } else {
                    Log.e(TAG, "Tag não suporta NDEF")
                    runOnUiThread {
                        Toast.makeText(this, "Tag não suporta NDEF", Toast.LENGTH_SHORT).show()
                    }
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Exceção geral: ${e.message}")
            e.printStackTrace()
        }
        
        return false
    }
    
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        
        // Processa a intent recebida
        if (NfcAdapter.ACTION_NDEF_DISCOVERED == intent.action ||
            NfcAdapter.ACTION_TAG_DISCOVERED == intent.action ||
            NfcAdapter.ACTION_TECH_DISCOVERED == intent.action) {
            
            Log.d(TAG, "Ação NFC detectada: ${intent.action}")
            
            // Se recebermos uma tag via intent, a processamos também
            val tag = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                intent.getParcelableExtra(NfcAdapter.EXTRA_TAG, Tag::class.java)
            } else {
                @Suppress("DEPRECATION")
                intent.getParcelableExtra(NfcAdapter.EXTRA_TAG)
            }
            
            if (tag != null) {
                Log.d(TAG, "Tag NFC recebida via intent")
                onTagDiscovered(tag)
            }
        }
    }
}

// Service para manter o NFC funcionando em background
class NfcService : android.app.Service() {
    private val TAG = "NFC_SERVICE"
    
    override fun onBind(intent: Intent?): android.os.IBinder? = null
    
    override fun onCreate() {
        super.onCreate()
        Log.d(TAG, "NFC Service criado")
    }
    
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.d(TAG, "NFC Service iniciado com código: ${MainActivity.currentCode}")
        return START_STICKY
    }
}

@Composable
fun WearApp(code: String, tagCount: Int, onGenerateNewCode: () -> Unit) {
    NFC_RelogioTheme {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colors.background),
            contentAlignment = Alignment.Center
        ) {
            TimeText()
            Column(
                modifier = Modifier.fillMaxWidth().padding(16.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    text = "Código NFC:",
                    textAlign = TextAlign.Center,
                    color = MaterialTheme.colors.primary,
                    fontSize = 14.sp
                )
                
                Spacer(modifier = Modifier.height(8.dp))
                
                // Exibe o código de forma mais destacada
                Text(
                    text = code,
                    textAlign = TextAlign.Center,
                    color = MaterialTheme.colors.primary,
                    fontSize = 30.sp,
                    fontWeight = androidx.compose.ui.text.font.FontWeight.Bold
                )
                
                if (tagCount > 0) {
                    Spacer(modifier = Modifier.height(4.dp))
                    
                    Text(
                        text = "Tags detectadas: $tagCount",
                        textAlign = TextAlign.Center,
                        color = MaterialTheme.colors.secondary,
                        fontSize = 10.sp
                    )
                    
                    Text(
                        text = "Última: ${MainActivity.lastTagId}",
                        textAlign = TextAlign.Center,
                        color = MaterialTheme.colors.secondary,
                        fontSize = 8.sp
                    )
                }
                
                Spacer(modifier = Modifier.height(8.dp))
                
                Text(
                    text = "Aproxime do celular para enviar",
                    textAlign = TextAlign.Center,
                    color = MaterialTheme.colors.primary,
                    fontSize = 12.sp
                )
                
                Spacer(modifier = Modifier.height(12.dp))
                
                Button(onClick = onGenerateNewCode) {
                    Text("Novo Código", fontSize = 12.sp)
                }
            }
        }
    }
}

@Preview(device = Devices.WEAR_OS_SMALL_ROUND, showSystemUi = true)
@Composable
fun DefaultPreview() {
    WearApp("123456", 0, onGenerateNewCode = {})
}