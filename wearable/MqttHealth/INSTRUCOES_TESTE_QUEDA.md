# 📱 Instruções para Testar Detecção de Queda

## ⚙️ Como Ativar o Modo Teste

1. **Abra o aplicativo MqttHealth**
2. **Navegue para a tela ACC** (botão "ACC" ou swipe para baixo)
3. **Ative o Modo Teste** - clique no botão "MODO TESTE"
   - O botão ficará vermelho com texto "DESATIVAR TESTE"
   - O status do detector ficará laranja
   - Os thresholds serão ajustados para facilitar os testes

## 🧪 Testes Recomendados

### Teste 1: Movimento Rápido Simples
- **Segure o celular firmemente**
- **Mova rapidamente para baixo e pare abruptamente**
- **Observe o "txtDebugInfo" para ver os valores de magnitude**

### Teste 2: Simulação de Queda Livre
- **Segure o celular acima da altura do peito**
- **Deixe cair em uma superfície macia (cama, sofá)**
- **⚠️ Cuidado para não danificar o dispositivo**

### Teste 3: Movimento Brusco com Parada
- **Acelere o celular rapidamente**
- **Pare abruptamente contra sua mão**
- **Repita várias vezes se necessário**

### Teste 4: Rotação + Aceleração
- **Gire o celular enquanto o move rapidamente**
- **Combine movimentos de rotação com aceleração**

## 📊 Valores para Monitorar

### No Modo Normal:
- **Queda Livre**: < 4.0 m/s²
- **Impacto**: > 15.0 m/s²
- **Duração**: > 100ms

### No Modo Teste:
- **Queda Livre**: < 6.0 m/s²
- **Impacto**: > 12.0 m/s²
- **Duração**: > 50ms

## 🚨 O Que Esperar

1. **Status "Queda Livre"** - quando a magnitude cai abaixo do threshold
2. **Status "Impacto Detectado"** - quando há impacto após queda livre
3. **Alerta de Queda** - popup vermelho com countdown de 5 segundos
4. **Vibração** - o dispositivo vibra durante o alerta

## 🛠️ Resolução de Problemas

### Se não detectar queda:
1. **Verifique se o Modo Teste está ativo**
2. **Observe os valores de magnitude no debug**
3. **Tente movimentos mais bruscos**
4. **Reinicie o aplicativo se necessário**

### Se detectar muitas quedas falsas:
1. **Desative o Modo Teste**
2. **Os valores normais são mais restritivos**
3. **Evite movimentos muito bruscos durante uso normal**

## 📱 Dicas Importantes

- **Use em ambiente seguro** para evitar danos ao dispositivo
- **Mantenha a tela ligada** durante os testes
- **Observe o txtDebugInfo** para valores em tempo real
- **O detector tem um buffer de suavização** que pode atrasar a detecção
- **Cada teste precisa de 2-3 segundos entre tentativas**

## 🔧 Ajustes Técnicos

Se ainda não detectar, você pode ajustar os valores no arquivo:
`MqttHealth/app/src/main/java/com/example/mqttwearable/sensors/FallDetector.kt`

Linhas de interesse:
- `TEST_FREE_FALL_THRESHOLD = 6.0f` (aumentar para ser menos sensível)
- `TEST_IMPACT_THRESHOLD = 12.0f` (diminuir para ser mais sensível)
- `TEST_FREE_FALL_DURATION_MS = 50L` (diminuir para detectar mais rápido) 