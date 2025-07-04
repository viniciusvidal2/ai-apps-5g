package com.sae5g.mqttwearable.mqtt

import android.util.Base64
import android.util.Log
import javax.crypto.Cipher
import javax.crypto.spec.SecretKeySpec
import javax.crypto.spec.IvParameterSpec
import java.security.SecureRandom

class AESCrypto {
    companion object {
        private const val ALGORITHM = "AES"
        private const val TRANSFORMATION = "AES/CBC/PKCS7Padding"
        private const val KEY_LENGTH = 16 // 128 bits
        private const val IV_LENGTH = 16 // 128 bits
        
        // Chave base64 fornecida pelo usuário
        private const val BASE64_KEY = "MZEaLIx8HCyoucOqqt2Tb73hUAZPT0Z7bti+JLLbDOUwQDFtyrN2JbrX2LNIf44s634JgmbiqVZVodOThH1uwoYORMvFxsA3ziWGUJZa3waazDJtaFbE54co/RRiSkvrGsr5Knl8VFl8M/yVbpcvOdNd5eRtye12ySLV78CNkkr/ryNwMtyWZwxRQuAcjPkO"
        
        // Chave AES 128 bits derivada da chave base64
        private val aesKey: SecretKeySpec by lazy {
            try {
                // Decodificar a chave base64 e usar apenas os primeiros 16 bytes para AES 128
                val keyBytes = Base64.decode(BASE64_KEY, Base64.DEFAULT)
                val truncatedKey = keyBytes.copyOfRange(0, KEY_LENGTH)
                SecretKeySpec(truncatedKey, ALGORITHM)
            } catch (e: Exception) {
                Log.e("AESCrypto", "Erro ao processar chave: ${e.message}")
                // Chave de fallback se houver erro
                SecretKeySpec(ByteArray(KEY_LENGTH) { 0 }, ALGORITHM)
            }
        }
        
        /**
         * Criptografa uma mensagem usando AES 128 bits
         * @param plaintext Texto a ser criptografado
         * @return String base64 contendo IV + dados criptografados
         */
        fun encrypt(plaintext: String): String? {
            return try {
                val cipher = Cipher.getInstance(TRANSFORMATION)
                
                // Gerar IV aleatório
                val iv = ByteArray(IV_LENGTH)
                SecureRandom().nextBytes(iv)
                val ivSpec = IvParameterSpec(iv)
                
                // Inicializar cipher para criptografia
                cipher.init(Cipher.ENCRYPT_MODE, aesKey, ivSpec)
                
                // Criptografar dados
                val encryptedData = cipher.doFinal(plaintext.toByteArray(Charsets.UTF_8))
                
                // Concatenar IV + dados criptografados
                val result = ByteArray(IV_LENGTH + encryptedData.size)
                System.arraycopy(iv, 0, result, 0, IV_LENGTH)
                System.arraycopy(encryptedData, 0, result, IV_LENGTH, encryptedData.size)
                
                // Retornar como base64
                Base64.encodeToString(result, Base64.DEFAULT)
            } catch (e: Exception) {
                Log.e("AESCrypto", "Erro ao criptografar: ${e.message}")
                null
            }
        }
        
        /**
         * Descriptografa uma mensagem criptografada
         * @param encryptedBase64 String base64 contendo IV + dados criptografados
         * @return Texto descriptografado ou null se houver erro
         */
        fun decrypt(encryptedBase64: String): String? {
            return try {
                val encryptedData = Base64.decode(encryptedBase64, Base64.DEFAULT)
                
                // Extrair IV e dados criptografados
                val iv = encryptedData.copyOfRange(0, IV_LENGTH)
                val cipherText = encryptedData.copyOfRange(IV_LENGTH, encryptedData.size)
                
                val cipher = Cipher.getInstance(TRANSFORMATION)
                val ivSpec = IvParameterSpec(iv)
                
                // Inicializar cipher para descriptografia
                cipher.init(Cipher.DECRYPT_MODE, aesKey, ivSpec)
                
                // Descriptografar dados
                val decryptedData = cipher.doFinal(cipherText)
                
                String(decryptedData, Charsets.UTF_8)
            } catch (e: Exception) {
                Log.e("AESCrypto", "Erro ao descriptografar: ${e.message}")
                null
            }
        }
    }
} 