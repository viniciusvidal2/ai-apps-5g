# 🧪 Teste Automático de Queda - MqttHealth

## 🚀 Como Usar o Teste Automático

### 1. **Preparação**
- Abra o aplicativo MqttHealth
- Navegue para a tela ACC (botão "ACC" ou swipe para baixo)
- Encontre o botão "🧪 TESTE AUTOMÁTICO"

### 2. **Iniciando o Teste**
- Clique em "🧪 TESTE AUTOMÁTICO"
- O botão mudará para "CANCELAR TESTE" (vermelho)
- Você verá a mensagem: "🚀 TESTE INICIADO - Solte o relógio!"
- A área de debug mostrará instruções

### 3. **Executando o Teste**
- **Segure o relógio/celular firmemente**
- **Solte-o de uma altura segura** (30-50cm é suficiente)
- **Deixe cair em superfície macia** (cama, sofá, almofada)
- **O teste detecta automaticamente:**
  - ⬇️ Início da queda (quando detecta queda livre)
  - 💥 Impacto (quando para abruptamente)
  - 🔄 Fim automático do teste

## 📊 O Que o Teste Coleta

### Durante a Queda:
- **Magnitude da aceleração** em tempo real
- **Coordenadas X, Y, Z** do acelerômetro
- **Timestamps** de cada medição
- **Estados detectados** (Monitorando → Queda Livre → Impacto)

### Relatório Final:
```
🎯 RESULTADO DO TESTE DE QUEDA

⏱️ Duração: 450ms
📊 Magnitude Mín: 2.34 m/s²
📈 Magnitude Máx: 18.67 m/s²
📊 Magnitude Média: 8.45 m/s²

📝 Dados coletados: 45 pontos

🔍 Estados detectados:
MONITORANDO: 15 pontos
QUEDA_LIVRE: 12 pontos
IMPACTO: 18 pontos

✅ Teste completado com sucesso!
```

## 🎯 O Que Esperar

### **Início do Teste:**
- Status: "🚀 TESTE INICIADO - Solte o relógio!"
- Botão vermelho: "CANCELAR TESTE"
- Coleta de dados em background

### **Durante a Queda:**
- Detecção automática da queda livre
- Coleta contínua de dados
- Monitoramento em tempo real

### **Após o Impacto:**
- Detecção automática do impacto
- Finalização automática em 500ms
- Exibição do relatório completo
- Botão volta ao normal: "🧪 TESTE AUTOMÁTICO"

## ⚠️ Dicas de Segurança

- **Use superfície macia** para evitar danos
- **Altura moderada** (30-50cm é suficiente)
- **Ambiente controlado** sem obstáculos
- **Segure firme** antes de soltar
- **Não teste em superfícies duras**

## 🔧 Parâmetros de Detecção

### **Detecção de Queda Livre:**
- Magnitude < 6.0 m/s²
- Duração mínima: 50ms

### **Detecção de Impacto:**
- Magnitude > 12.0 m/s²
- Após período de queda livre válido

### **Finalização:**
- Automática após impacto
- Delay de 500ms para coletar dados pós-impacto

## 🛠️ Resolução de Problemas

### **Se não detectar queda:**
- Verifique se soltou o dispositivo
- Tente altura maior (até 1 metro)
- Use superfície mais macia
- Reinicie o teste

### **Se não detectar impacto:**
- Deixe cair em superfície mais firme (mas ainda segura)
- Evite superfícies muito macias que absorvem o impacto
- Tente ângulo diferente de queda

### **Para cancelar:**
- Clique em "CANCELAR TESTE" a qualquer momento
- O teste para imediatamente
- Dados parciais podem ser perdidos

## 📈 Interpretação dos Resultados

### **Valores Normais:**
- **Duração total:** 200-1000ms
- **Magnitude mínima:** 2-6 m/s² (queda livre)
- **Magnitude máxima:** 12-30 m/s² (impacto)

### **Indicadores de Sucesso:**
- Detectou estados: MONITORANDO → QUEDA_LIVRE → IMPACTO
- Duração razoável da queda livre
- Pico claro de impacto
- Dados coletados > 20 pontos

🎉 **O teste automático torna muito mais fácil testar a detecção de queda!** 