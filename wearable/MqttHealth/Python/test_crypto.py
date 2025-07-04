#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Teste para verificar se a criptografia/descriptografia está funcionando corretamente
Este arquivo simula o que o aplicativo Android faz e testa a descriptografia
"""

import base64
import json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import secrets

# Mesma chave usada no Android e no main.py
BASE64_KEY = "MZEaLIx8HCyoucOqqt2Tb73hUAZPT0Z7bti+JLLbDOUwQDFtyrN2JbrX2LNIf44s634JgmbiqVZVodOThH1uwoYORMvFxsA3ziWGUJZa3waazDJtaFbE54co/RRiSkvrGsr5Knl8VFl8M/yVbpcvOdNd5eRtye12ySLV78CNkkr/ryNwMtyWZwxRQuAcjPkO"

def get_aes_key():
    """Deriva a chave AES 128 bits da chave base64"""
    key_bytes = base64.b64decode(BASE64_KEY)
    return key_bytes[:16]  # Primeiros 16 bytes para AES-128

def encrypt_message(plaintext):
    """
    Criptografa uma mensagem usando AES-128-CBC (simula o Android)
    
    Args:
        plaintext: String a ser criptografada
    
    Returns:
        String base64 com IV + dados criptografados
    """
    try:
        # Converter para bytes
        plaintext_bytes = plaintext.encode('utf-8')
        
        # Gerar IV aleatório
        iv = secrets.token_bytes(16)
        
        # Aplicar padding PKCS7
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext_bytes) + padder.finalize()
        
        # Criar cipher AES-128-CBC
        cipher = Cipher(
            algorithms.AES(get_aes_key()),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Criptografar dados
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        
        # Concatenar IV + dados criptografados
        result = iv + encrypted_data
        
        # Retornar como base64
        return base64.b64encode(result).decode('ascii')
        
    except Exception as e:
        print(f"Erro ao criptografar: {e}")
        return None

def decrypt_message(encrypted_base64):
    """
    Descriptografa uma mensagem criptografada com AES-128-CBC
    (mesmo código do main.py)
    
    Args:
        encrypted_base64: String base64 contendo IV + dados criptografados
    
    Returns:
        String descriptografada ou None se houver erro
    """
    try:
        # Decodificar base64
        encrypted_data = base64.b64decode(encrypted_base64)
        
        # Extrair IV (primeiros 16 bytes) e dados criptografados
        iv = encrypted_data[:16]
        cipher_text = encrypted_data[16:]
        
        # Criar cipher AES-128-CBC
        cipher = Cipher(
            algorithms.AES(get_aes_key()),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # Descriptografar dados
        decrypted_data = decryptor.update(cipher_text) + decryptor.finalize()
        
        # Remover padding PKCS7
        unpadder = padding.PKCS7(128).unpadder()
        unpadded_data = unpadder.update(decrypted_data) + unpadder.finalize()
        
        # Retornar como string UTF-8
        return unpadded_data.decode('utf-8')
        
    except Exception as e:
        print(f"Erro ao descriptografar: {e}")
        return None

def test_encryption_decryption():
    """Testa a criptografia e descriptografia"""
    print("🔧 Testando Criptografia/Descriptografia AES-128-CBC")
    print("=" * 60)
    
    # Mensagens de teste (simulando o que o Android envia)
    test_messages = [
        # Dados de saúde
        '{"time":"2024-01-01T12:00:00Z","heartRateBpm":72,"spo2":98,"id":"device123","latitude":-23.550520,"longitude":-46.633308}',
        
        # Alerta de queda
        '{"time":"2024-01-01T12:00:00Z","fall":1,"id":"device123","latitude":-23.550520,"longitude":-46.633308}',
        
        # Dados do acelerômetro
        '{"time":"2024-01-01T12:00:00Z","id":"device123","accelerometer":{"x":0.12,"y":0.34,"z":9.81}}',
        
        # Mensagem simples
        "Hello, World!"
    ]
    
    for i, original_message in enumerate(test_messages, 1):
        print(f"\n📝 Teste {i}")
        print(f"📄 Mensagem original: {original_message}")
        
        # Criptografar
        encrypted = encrypt_message(original_message)
        if encrypted:
            print(f"🔐 Mensagem criptografada: {encrypted}")
            
            # Descriptografar
            decrypted = decrypt_message(encrypted)
            if decrypted:
                print(f"🔓 Mensagem descriptografada: {decrypted}")
                
                # Verificar se a descriptografia foi bem-sucedida
                if decrypted == original_message:
                    print("✅ SUCESSO: Criptografia e descriptografia funcionaram!")
                else:
                    print("❌ ERRO: Mensagem descriptografada não confere!")
            else:
                print("❌ ERRO: Falha ao descriptografar!")
        else:
            print("❌ ERRO: Falha ao criptografar!")
        
        print("_" * 60)

if __name__ == "__main__":
    test_encryption_decryption() 