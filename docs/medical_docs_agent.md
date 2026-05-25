# Medical Docs Agent

We will cover the basic working principles for the Medical Docs Agent, how to install the environment, and how to build and run each of its components. The agent is composed of three main entry points: a **REST API server**, a **Streamlit visual interface**, and a **folder management service**.

## Working concept

The agent processes medical PDF documents through a two-stage pipeline:

1. **OCR Extraction** — Each PDF page is converted to an image and text is extracted either via **PaddleOCR** (fast, local) or via an **LLM-based OCR** model (`glm-ocr:latest`) running inside Ollama.
2. **Classification** — The extracted text is passed to a language model (`gemma4:latest` by default) that assigns a category from a configurable list of medical document classes defined in `modules/configs/document_classes.yaml`.

Once classified, the documents (PDF and extracted `.md` text files) are organized into category-specific subfolders inside a designated output folder.

The pipeline runs asynchronously in a background thread. Status is tracked via a state flag (`idle`, `running`, `completed`, `failed`).

---

## Installing the environment

The agent requires the **`ocr` Conda environment**. Create and activate it, then install the dependencies:

```bash
conda create -n ocr python=3.10
conda activate ocr
cd ai-apps-5g
pip install -r medical_docs_agent/requirements.txt
```

> **Note:** PaddleOCR and its dependencies can be large. Ensure you have at least 4 GB of free disk space and a stable internet connection for the initial install.

---

## Setting Ollama models

The agent requires Ollama to be installed and running on the host. You can install Ollama with:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Then pull the required models:

```bash
# Mandatory for LLM-based OCR extraction
ollama pull glm-ocr:latest

# Mandatory for document classification
ollama pull gemma4:latest
```

You can find additional models at the [Ollama library](https://ollama.com/library).

---

## Document classes configuration

The list of medical document categories is stored in:

```
medical_docs_agent/modules/configs/document_classes.yaml
```

Each entry has a `name` and a `description` used by the classification LLM. You can add or remove classes by editing this file directly or through the Streamlit interface. The current default classes are:

- `fisioterapia`
- `cardiologia`
- `eletroencefalograma`
- `psicosocial`
- `pulmonar`
- `ergonomia`
- `hemograma`
- `odontologico`

---

## Agent 1 — REST API Server (`medical_docs_agent.py`)

The REST API server exposes HTTP endpoints to submit classification jobs and poll their status asynchronously. It defaults to port **8002**.

### Running locally

```bash
cd ai-apps-5g/medical_docs_agent
python medical_docs_agent.py \
  --host 0.0.0.0 \
  --port 8002 \
  --data_yaml_path modules/configs/document_classes.yaml \
  --output_folder /path/to/output/classified_docs
```

### Available endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Returns a welcome message |
| `GET` | `/health` | Returns the health status of the API |
| `POST` | `/ocr/classify` | Submits a list of PDF paths for classification |
| `GET` | `/ocr/status/{job_id}` | Polls the status and results of a running job |

### Example classify request (curl)

```bash
curl -X POST http://127.0.0.1:8002/ocr/classify \
  -H "Content-Type: application/json" \
  -d '{
    "document_paths": ["/absolute/path/to/document.pdf"],
    "ocr_method": "paddle",
    "classification_model": "gemma4:latest"
  }'
```

### Running the tests

Use the test script to exercise all API endpoints against a running server. Replace `--document_paths` with the absolute path to a real PDF:

```bash
cd ai-apps-5g/medical_docs_agent
python medical_docs_agent_test.py \
  --base_url http://127.0.0.1:8002 \
  --document_paths /absolute/path/to/document.pdf \
  --ocr_method paddle \
  --model gemma4:latest
```

The test script will:
1. Wait for the API to become available (up to 60 seconds).
2. Test the root and health endpoints.
3. Submit a classification job using PaddleOCR and poll until completion.
4. Print a classification summary for each document.

A successful run ends with:

```
All tests passed! ✅
```

---

## Agent 2 — Streamlit Visual Interface (`medical_docs_agent_interface.py`)

The Streamlit interface provides a visual, browser-based UI to upload PDFs, run OCR and classification, browse results, and manage the document classes configuration.

### Running locally

```bash
cd ai-apps-5g/medical_docs_agent
streamlit run medical_docs_agent_interface.py
```

The interface will open automatically in your default browser at `http://localhost:8501`. No additional arguments are required — the interface auto-detects the `modules/configs/document_classes.yaml` configuration file.

---

## Agent 3 — Folder Management Service (`medical_docs_agent_folder_management.py`)

The folder management service runs a periodic inspection loop that monitors an input folder for new medical PDF documents and automatically classifies them. Processed files are tracked in a state YAML file so that only new, unprocessed files are passed through the pipeline on each run.

### Running locally

```bash
cd ai-apps-5g/medical_docs_agent
python medical_docs_agent_folder_management.py \
  --input-folder /path/to/input_pdfs \
  --output-folder /path/to/classified_output \
  --interval 5
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--input-folder` | ✅ | — | Directory containing input PDF files |
| `--output-folder` | ✅ | — | Directory where classified PDFs and `.md` extracts will be organized |
| `--interval` | ✅ | — | Inspection interval in minutes (supports decimals, e.g. `0.5` for 30 seconds) |
| `--state-yaml` | ❌ | `modules/configs/folder_manager_state.yaml` | Custom path to the YAML state file |

The service will run indefinitely until stopped with **Ctrl+C**, which triggers a clean shutdown that stops any active Ollama model processes.

### State file structure

The state is persisted in a YAML file structured as a root **list of dictionaries**, one per monitored directory. This allows multiple independent instances or runs to track different folders in the same file without interference:

```yaml
- input_folder: /path/to/input_a
  output_folder: /path/to/output_a
  last_checked_files:
    - /path/to/input_a/document_1.pdf
  processed_files:
    - /path/to/input_a/document_1.pdf
- input_folder: /path/to/input_b
  output_folder: /path/to/output_b
  last_checked_files:
    - /path/to/input_b/document_2.pdf
  processed_files: []
```

---

## Docker (Folder Management Service)

The Dockerfile packages the folder management service with all system dependencies, Python packages, and Ollama models pre-baked into the image.

### Building the image

Run from the root of the workspace. Pull `glm-ocr:latest` and `gemma4:latest` at build time:

```bash
docker build -t medical_docs_agent_image \
  -f medical_docs_agent/Dockerfile \
  --build-arg OLLAMA_MODELS_TO_PULL="glm-ocr:latest gemma4:latest" .
```

### Preparing the state YAML file on the host

The container writes folder tracking state back to a YAML file. To share this file with the host (so state persists across container restarts), you must **create the file on the host before running the container**. Docker requires the file to already exist for a single-file bind mount — if it does not exist, Docker will create a directory at that path instead.

Create an empty state file on your host:

```bash
touch /absolute/path/to/host/folder_manager_state.yaml
```

If you already have an existing state file (e.g., from a previous local run), you can use it directly — the container will pick up its contents and continue from where it left off.

### Running the container

Mount the host input folder, output folder, **and state YAML file** into the container. Pass the container-side path of the state file via `--state-yaml`:

```bash
docker run --rm -d \
  -v /absolute/path/to/host/input_folder:/app/input \
  -v /absolute/path/to/host/output_folder:/app/output \
  -v /absolute/path/to/host/folder_manager_state.yaml:/app/state.yaml \
  --name medical_docs_agent \
  medical_docs_agent_image \
  --input-folder /app/input \
  --output-folder /app/output \
  --interval 5 \
  --state-yaml /app/state.yaml
```

**What each mount does:**

| Host path | Container path | Purpose |
|-----------|---------------|---------|
| `/absolute/path/to/host/input_folder` | `/app/input` | Directory the agent scans for new PDFs |
| `/absolute/path/to/host/output_folder` | `/app/output` | Directory where classified PDFs and `.md` files are written |
| `/absolute/path/to/host/folder_manager_state.yaml` | `/app/state.yaml` | Live-shared state file — the container reads and writes it; changes are immediately visible on the host |

Because the state file is a bind mount to the real host file, you can inspect or edit it at any time while the container is running:

```bash
cat /absolute/path/to/host/folder_manager_state.yaml
```

Remove `-d` to run in the foreground and view live logs. To stream logs from a detached container:

```bash
docker logs -f medical_docs_agent
```

### Verifying the container

1. Drop a PDF file into your host's input folder.
2. Check the container logs — you should see the agent detect the file, run OCR and classification, and organize the result.
3. Verify that a category subfolder (e.g., `cardiologia/`) has been created in your host's output folder containing both the `.pdf` and a `.md` text extract.
4. Inspect the host state file — you should see the processed file listed under `processed_files` for your input folder entry.
