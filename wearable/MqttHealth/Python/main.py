#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import paho.mqtt.client as mqtt
import base64
import json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import time

# Configurações MQTT
MQTT_HOST = "192.168.0.109"
MQTT_PORT = 1883
MQTT_TOPICS = ["health/data", "fall", "accelerometer"]

# Chave base64 do Android (mesma chave usada no aplicativo)
BASE64_KEY = "MZEaLIx8HCyoucOqqt2Tb73hUAZPT0Z7bti+JLLbDOUwQDFtyrN2JbrX2LNIf44s634JgmbiqVZVodOThH1uwoYORMvFxsA3ziWGUJZa3waazDJtaFbE54co/RRiSkvrGsr5Knl8VFl8M/yVbpcvOdNd5eRtye12ySLV78CNkkr/ryNwMtyWZwxRQuAcjPkO"

# Derivar chave AES 128 bits (primeiros 16 bytes da chave base64)
def get_aes_key():
    """Deriva a chave AES 128 bits da chave base64"""
    try:
        key_bytes = base64.b64decode(BASE64_KEY)
        return key_bytes[:16]  # Primeiros 16 bytes para AES-128
    except Exception as e:
        print(f"Erro ao processar chave: {e}")
        return b'\x00' * 16  # Chave de fallback

AES_KEY = get_aes_key()

def decrypt_message(encrypted_base64):
    """
    Descriptografa uma mensagem criptografada com AES-128-CBC
    
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
            algorithms.AES(AES_KEY),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # Descriptografar dados
        decrypted_data = decryptor.update(cipher_text) + decryptor.finalize()
        
        # Remover padding PKCS7
        padding_length = decrypted_data[-1]
        decrypted_data = decrypted_data[:-padding_length]
        
        # Retornar como string UTF-8
        return decrypted_data.decode('utf-8')
        
    except Exception as e:
        print(f"Erro ao descriptografar: {e}")
        return None

def format_json(json_str):
    """Formata JSON para exibição mais legível"""
    try:
        data = json.loads(json_str)
        return json.dumps(data, indent=2, ensure_ascii=False)
    except:
        return json_str

def on_connect(client, userdata, flags, rc):
    """Callback chamado quando conecta ao MQTT"""
    if rc == 0:
        print("✅ Conectado ao MQTT broker com sucesso!")
        print(f"📍 Servidor: {MQTT_HOST}:{MQTT_PORT}")
        print("📡 Inscrevendo-se nos tópicos...")
        
        # Inscrever-se em todos os tópicos
        for topic in MQTT_TOPICS:
            client.subscribe(topic)
            print(f"   • {topic}")
        
        print("\n🔄 Aguardando mensagens...\n")
        
    else:
        print(f"❌ Falha na conexão ao MQTT. Código: {rc}")

def on_message(client, userdata, msg):
    """Callback chamado quando uma mensagem chega"""
    topic = msg.topic
    encrypted_message = msg.payload.decode('utf-8')
    
    print("📨 Mensagem Chegou")
    print(f"📍 Tópico: {topic}")
    print(f"🔐 Mensagem criptografada: {encrypted_message}")
    
    # Tentar descriptografar
    decrypted_message = decrypt_message(encrypted_message)
    
    if decrypted_message:
        print(f"🔓 Mensagem descriptografada: {format_json(decrypted_message)}")
    else:
        print("❌ Falha ao descriptografar mensagem")
    
    print("_" * 80)
    print()

def on_disconnect(client, userdata, rc):
    """Callback chamado quando desconecta do MQTT"""
    print(f"🔌 Desconectado do MQTT broker. Código: {rc}")

def main():
    """Função principal"""
    print("🚀 Iniciando Cliente MQTT Descriptografador")
    print(f"🔑 Chave AES: {AES_KEY.hex()[:32]}...")
    print("=" * 80)
    
    # Criar cliente MQTT
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect
    
    try:
        # Conectar ao broker
        print(f"🔗 Conectando ao broker MQTT {MQTT_HOST}:{MQTT_PORT}...")
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        
        # Iniciar loop para processar mensagens
        client.loop_forever()
        
    except KeyboardInterrupt:
        print("\n⏹️  Interrompido pelo usuário")
        client.disconnect()
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        
    finally:
        print("👋 Encerrando cliente MQTT...")

if __name__ == "__main__":
    main() 