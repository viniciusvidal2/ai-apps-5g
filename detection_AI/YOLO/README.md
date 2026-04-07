# Detection AI - Documentação do Projeto

Este repositório/pasta contém uma coleção de scripts em Python desenvolvidos para o treinamento, processamento de dados e inferência de modelos de Visão Computacional (principalmente YOLO e Roboflow) focados na detecção de Equipamentos de Proteção Individual (EPIs).

Abaixo está o detalhamento de cada arquivo `.py` e sua respectiva função dentro do projeto.

---

## 📁 Arquivos na Raiz (`/`)

### `Video.py`
Script que utiliza a API da Roboflow (via `InferenceHTTPClient` / `webrtc`) para processar um vídeo locamente enviando os frames para inferência remota. Ele captura as predições do modelo de EPIs e recria o vídeo de saída (`output.mp4`) com as inferências (bounding boxes) aplicadas.

### `Download_Data.py`
Script utilitário para **baixar um dataset** diretamente do Roboflow utilizando a API Key e a biblioteca `roboflow`. Útil para fazer o pull de novas versões dos dados para treinar localmente.

### `API_Down.py`
Script utilitário para **baixar os pesos de um modelo** (arquivo `.pt`) já treinado no Roboflow para o seu computador.

---

## 📁 Pasta `/Person`
Focada no processamento e anotação de dados específicos para a detecção de Pessoas (Person).

### `identificar_person.py`
Script de **Auto-Anotação (Auto-Labeling)**. Ele lê um dataset existente (pastas `train`, `valid`, `test`) que possui imagens e arquivos de texto (labels do YOLO). Ele executa um modelo YOLO (`person.pt`) em cada imagem para identificar pessoas, e automaticamente **adiciona** as coordenadas das pessoas encontradas nos arquivos `.txt` já existentes (preservando as anotações anteriores de EPIs).

### `UPLOAD.py`
Script para realizar o **upload em lote (multithreading)** de imagens e seus respectivos labels (que foram processados no script anterior) para um novo projeto/versão no Roboflow. Ele gerencia o envio simultâneo de imagens e anotações utilizando múltiplas threads para otimizar o tempo de envio.

---

## 📁 Pasta `/TesteVideo`
Voltada para realizar inferências de teste em vídeos locais com modelos baixados.

### `main.py`
Script de inferência via CLI. Permite que você:
1. Selecione um Tracker de objetos (ByteTrack ou BoT-SORT).
2. Escolha um ou mais modelos de IA salvos na pasta.
3. Escolha um ou mais vídeos para processar.
Ele rastreia os objetos (Track), desenha as caixas no vídeo e exporta os vídeos salvos na pasta `Output` em formato H.264 (compatível com WhatsApp e Navegadores) utilizando `ffmpeg`.

### `Teste.py`
Script avançado de inferência logica com verificação de status. Diferente do `main.py`, ele:
1. Realiza o rastreamento (tracking) exclusivo das **pessoas**.
2. Realiza a **detecção** dos EPIs soltos na imagem.
3. Faz um cálculo geométrico (Center Containment ou IoU) para **vincular o EPI à pessoa** correta.
4. Renderiza no vídeo um quadro de verificação, exibindo uma caixa verde (OK) caso todos os EPIs obrigatórios estejam presentes, ou uma caixa vermelha listando os EPIs que estão faltosos na pessoa correspondente.

---

## 📁 Pasta `/TesteVideo/Modelos`
Contém scripts para utilitários de manipulação da estrutura interna de arquivos `.pt` (PyTorch) do YOLO.

### `print_classes.py`
Script de diagnóstico. Ele carrega os pesos dos modelos (`.pt`, `.engine`, etc.) da pasta e imprime no terminal a lista de classes internas do modelo revelando os IDs atrelados aos nomes que foram configurados durante o treinamento.

### `rename_classes.py`
Script utilitário para manipular e **renomear as classes** internamente nos pesos de um modelo treinado. Ele carrega o modelo, altera o dicionário `model.names` (por exemplo, mudando os IDs para nomes legíveis ou adaptando ao código) e salva um novo arquivo `.pt` modificado.
