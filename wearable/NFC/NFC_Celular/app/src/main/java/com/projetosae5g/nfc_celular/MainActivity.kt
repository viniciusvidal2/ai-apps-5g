package com.projetosae5g.nfc_celular

import android.app.PendingIntent
import android.content.Intent
import android.nfc.NdefMessage
import android.nfc.NfcAdapter
import android.os.Build
import android.os.Bundle
import android.os.Parcelable
import android.util.Log
import android.widget.TextView
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat

/**
 * Aplicativo para leitura de códigos NFC enviados pelo relógio Samsung Watch 7.
 * 
 * Este aplicativo processa mensagens NDEF enviadas pelo relógio e exibe os códigos de 6 dígitos.
 * A comunicação funciona da seguinte forma:
 * 1. O relógio gera um código aleatório de 6 dígitos
 * 2. Quando o relógio é aproximado do celular, ele escreve o código em uma mensagem NDEF
 * 3. Este aplicativo lê a mensagem NDEF e extrai o código
 * 
 * Funcionalidades:
 * - Detecção automática de mensagens NFC quando o app está em primeiro plano
 * - Processamento de registros NDEF de texto para extrair o código
 * - Exibição do código na interface do usuário
 */
class MainActivity : AppCompatActivity() {
    
    private var nfcAdapter: NfcAdapter? = null
    private lateinit var statusTextView: TextView
    private lateinit var codeTextView: TextView
    private lateinit var messageTextView: TextView
    private lateinit var pendingIntent: PendingIntent
    private val TAG = "NFC_CELULAR"
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_main)
        
        // Inicializa as views
        statusTextView = findViewById(R.id.statusTextView)
        codeTextView = findViewById(R.id.codeTextView)
        messageTextView = findViewById(R.id.messageTextView)
        
        // Configura o adaptador NFC
        nfcAdapter = NfcAdapter.getDefaultAdapter(this)
        
        if (nfcAdapter == null) {
            statusTextView.text = "Este dispositivo não suporta NFC"
            Toast.makeText(this, "Este dispositivo não suporta NFC", Toast.LENGTH_LONG).show()
            Log.e(TAG, "NFC não suportado neste dispositivo")
        } else {
            statusTextView.text = "Aguardando conexão NFC..."
            Log.d(TAG, "Adaptador NFC inicializado, aguardando conexão")
        }
        
        // Cria um PendingIntent para lidar com as tags NFC descobertas
        val intent = Intent(this, javaClass).apply {
            addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
        }
        pendingIntent = PendingIntent.getActivity(this, 0, intent, 
            PendingIntent.FLAG_MUTABLE)
        
        // Verifica se a app foi iniciada por uma tag NFC
        handleIntent(intent)
        
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main)) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }
    }
    
    override fun onResume() {
        super.onResume()
        // Configura o adapter para interceptar mensagens NFC quando o app estiver no foreground
        nfcAdapter?.enableForegroundDispatch(this, pendingIntent, null, null)
        Log.d(TAG, "onResume: foreground dispatch habilitado")
    }
    
    override fun onPause() {
        super.onPause()
        // Desativa o foreground dispatch
        nfcAdapter?.disableForegroundDispatch(this)
        Log.d(TAG, "onPause: foreground dispatch desabilitado")
    }
    
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        // Processa a intent quando uma tag NFC é detectada
        handleIntent(intent)
    }
    
    // Processa o intent recebido pelo NFC
    private fun handleIntent(intent: Intent) {
        Log.d(TAG, "handleIntent: ${intent.action}")
        
        // Verifica todos os tipos de intents NFC
        val action = intent.action
        if (NfcAdapter.ACTION_NDEF_DISCOVERED == action ||
            NfcAdapter.ACTION_TECH_DISCOVERED == action ||
            NfcAdapter.ACTION_TAG_DISCOVERED == action) {
            
            Log.d(TAG, "Ação NFC detectada: $action")
            
            // Mostra a intent para depuração
            intent.extras?.keySet()?.forEach { key ->
                Log.d(TAG, "Extra - $key: ${intent.extras?.get(key)}")
            }
            
            // Tenta extrair mensagens NDEF
            processNdefMessages(intent)
        }
    }
    
    // Processa a mensagem NFC recebida
    private fun processNdefMessages(intent: Intent) {
        try {
            // Extrai o ID da tag (MAC)
            val tagId = intent.getByteArrayExtra(NfcAdapter.EXTRA_ID)?.let { id ->
                id.joinToString(":") { "%02X".format(it) }
            } ?: "Desconhecido"
            
            Log.d(TAG, "ID da tag: $tagId")
            
            // Extrai mensagens NDEF do intent
            val rawMessages: Array<Parcelable>? = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                intent.getParcelableArrayExtra(NfcAdapter.EXTRA_NDEF_MESSAGES, Parcelable::class.java)
            } else {
                @Suppress("DEPRECATION")
                intent.getParcelableArrayExtra(NfcAdapter.EXTRA_NDEF_MESSAGES)
            }
            
            Log.d(TAG, "Mensagens NDEF encontradas: ${rawMessages?.size ?: 0}")
            
            var messageProcessed = false
            
            // Tenta extrair do NDEF
            if (rawMessages != null && rawMessages.isNotEmpty()) {
                Log.d(TAG, "Processando mensagens NDEF")
                
                // Processa a primeira mensagem
                val ndefMessage = rawMessages[0] as NdefMessage
                val records = ndefMessage.records
                
                if (records.isNotEmpty()) {
                    Log.d(TAG, "Registros encontrados: ${records.size}")
                    
                    // Extrai o conteúdo do primeiro registro
                    val payload = records[0].payload
                    
                    // Mostra o payload bruto para depuração
                    Log.d(TAG, "Payload bruto: ${payload.joinToString(":") { "%02X".format(it) }}")
                    
                    // Para registros de texto, o primeiro byte indica o tamanho do código de idioma
                    val languageCodeLength = payload[0].toInt() and 0x3F
                    val actualTextBytes = payload.copyOfRange(languageCodeLength + 1, payload.size)
                    val fullMessage = String(actualTextBytes)
                    
                    // Exibe a mensagem completa no TextView dedicado
                    statusTextView.text = "Mensagem NFC recebida!"
                    messageTextView.text = fullMessage
                    
                    // Adiciona um log com a mensagem completa
                    Log.d(TAG, "Mensagem extraída: '$fullMessage'")
                    
                    // Mostra a mensagem como toast para depuração
                    Toast.makeText(this, "Recebido: $fullMessage", Toast.LENGTH_LONG).show()
                    
                    // Tenta processar no formato: ID=xxx,ORIGEM=yyy,CODIGO=zzz
                    if (fullMessage.contains("CODIGO=")) {
                        try {
                            // Divide a mensagem em pares chave-valor
                            val parts = fullMessage.split(",")
                            var id = ""
                            var origem = ""
                            var codigo = ""
                            
                            // Extrai os valores de cada parte
                            for (part in parts) {
                                Log.d(TAG, "Processando parte: $part")
                                when {
                                    part.startsWith("ID=") -> id = part.substring(3)
                                    part.startsWith("ORIGEM=") -> origem = part.substring(7)
                                    part.startsWith("CODIGO=") -> codigo = part.substring(7)
                                }
                            }
                            
                            Log.d(TAG, "ID: $id, Origem: $origem, Código: $codigo")
                            
                            // Valida se temos valores válidos
                            if (codigo.isNotEmpty() && codigo.length == 6) {
                                // Atualiza a UI com as informações extraídas
                                codeTextView.text = "ID: $id\nOrigem: $origem\nCódigo: $codigo"
                                messageProcessed = true
                            } else {
                                Log.d(TAG, "Código inválido ou vazio: '$codigo'")
                                codeTextView.text = "Código inválido ou vazio"
                            }
                        } catch (e: Exception) {
                            Log.e(TAG, "Erro ao processar formato chave-valor: ${e.message}")
                            codeTextView.text = "Erro ao processar mensagem: ${e.message}"
                        }
                    } else if (fullMessage.length >= 6) {
                        // Tenta extrair um código de 6 dígitos diretamente da mensagem
                        val codeMatch = "\\d{6}".toRegex().find(fullMessage)
                        if (codeMatch != null) {
                            val codigo = codeMatch.value
                            Log.d(TAG, "Código de 6 dígitos encontrado: $codigo")
                            
                            statusTextView.text = "Código detectado!"
                            codeTextView.text = "ID: $tagId\nOrigem: relógio\nCódigo: $codigo"
                            messageProcessed = true
                        } else {
                            Log.d(TAG, "Nenhum código de 6 dígitos encontrado na mensagem")
                            codeTextView.text = "Nenhum código detectado na mensagem"
                        }
                    }
                } else {
                    Log.d(TAG, "Não há registros na mensagem NDEF")
                    messageTextView.text = "Sem dados na mensagem"
                    codeTextView.text = "Sem registros na mensagem NDEF"
                }
            } else {
                Log.d(TAG, "Não há mensagens NDEF no intent")
                messageTextView.text = "Sem mensagem NDEF"
                codeTextView.text = "Não foi possível obter mensagem NDEF"
            }
            
            // Se não conseguimos processar a mensagem de maneira estruturada
            if (!messageProcessed && messageTextView.text.isEmpty()) {
                Log.d(TAG, "Nenhuma mensagem NFC processada com sucesso")
                
                // Verifica se pelo menos temos o ID da tag
                if (tagId != "Desconhecido") {
                    statusTextView.text = "Tag NFC detectada!"
                    messageTextView.text = "Não foi possível extrair a mensagem"
                    codeTextView.text = "ID: $tagId\nOrigem: relógio\nCódigo: não detectado"
                } else {
                    statusTextView.text = "Tag NFC desconhecida detectada"
                    messageTextView.text = "Sem mensagem"
                    codeTextView.text = "Não foi possível extrair informações"
                }
                
                // Registra todos os extras do intent para depuração
                intent.extras?.keySet()?.forEach { key ->
                    val value = intent.extras?.get(key)
                    Log.d(TAG, "Extra - $key: $value")
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Erro ao processar mensagem NFC: ${e.message}")
            e.printStackTrace()
            
            statusTextView.text = "Erro ao processar NFC"
            messageTextView.text = "Erro: ${e.message}"
            codeTextView.text = "Erro ao processar a mensagem NFC.\nVerifique os logs para mais detalhes."
        }
    }
}