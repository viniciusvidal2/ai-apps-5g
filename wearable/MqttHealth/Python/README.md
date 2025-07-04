# Cliente MQTT Descriptografador

Este projeto Python conecta ao broker MQTT e descriptografa mensagens criptografadas enviadas pelo aplicativo Android wearable.

## Estrutura do Projeto

```
Python/
├── venv/           # Ambiente virtual Python
├── main.py         # Programa principal
├── requirements.txt # Dependências
└── README.md       # Este arquivo
```

## Instalação e Uso

### 1. Ativar o ambiente virtual

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/macOS:**
```bash
source venv/bin/activate
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Executar o programa

```bash
python main.py
```

## Configuração

### IP do Broker MQTT

Por padrão, o programa conecta em `192.168.0.109:1883`. Para alterar:

1. Abra o arquivo `main.py`
2. Modifique a linha:
   ```python
   MQTT_HOST = "192.168.0.109"
   ```

### Tópicos Monitorados

O programa escuta nos seguintes tópicos:
- `/health/data` - Dados de saúde
- `/fall` - Alertas de queda
- `/accelerometer` - Dados do acelerômetro

## Funcionamento

1. **Conexão**: Conecta ao broker MQTT
2. **Inscrição**: Inscreve-se nos tópicos configurados
3. **Recepção**: Aguarda mensagens criptografadas
4. **Descriptografia**: Descriptografa usando AES-128-CBC
5. **Exibição**: Mostra a mensagem original e descriptografada

## Formato da Saída

```
📨 Mensagem Chegou
📍 Tópico: /health/data
🔐 Mensagem criptografada: <base64_string>
🔓 Mensagem descriptografada: {
  "time": "2024-01-01T12:00:00Z",
  "heartRateBpm": 72,
  "id": "device123"
}
________________________________________________________________________________
```

## Criptografia

- **Algoritmo**: AES-128-CBC
- **Padding**: PKCS7
- **Chave**: Derivada da mesma chave base64 do aplicativo Android
- **IV**: Extraído dos primeiros 16 bytes da mensagem

## Dependências

- `paho-mqtt==1.6.1` - Cliente MQTT
- `cryptography==41.0.7` - Biblioteca de criptografia

## Parar o Programa

Para parar o programa, pressione `Ctrl+C`. 