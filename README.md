# ai-apps-5g
This repository will hold the codes for the AI apps we build in the 5G context

## Prerequisites

### System Updates
First, update your system packages:
```bash
sudo apt update && sudo apt upgrade -y
```

### Install Ollama
The application requires Ollama to be installed and running for LLM functionality:

1. Install curl if not already installed:
```bash
sudo apt install curl -y
```

2. Install Ollama:
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

3. Start the Ollama service:
```bash
sudo systemctl start ollama
```

Note: Keep the Ollama service running while using the application. You can check its status with:
```bash
sudo systemctl status ollama
```

## Reproducing the AI tools with conda environment
This instructions should run on a linux machine with a proper NVidia GPU installed. The actual test ran on a laptop i7 12th generation, 3050 RTX GPU.

To install Anaconda, follow the instructions in the [official website](https://www.anaconda.com/download). You should end up with a base environment in your terminal.

To create our environment to run the code in this repo, use the file ai_environment.yml and call the following command:

```bash
cd /path/to/this/repo
conda env create --file=ai_environment.yml
```

Cuda and tensorflow versions might need to adapt, but you should be able to run the example scripts after successful installation.

## Sample data
The audio file we are using as an example can be downloaded from [this google drive link](https://drive.google.com/file/d/1Y_76o_JHO1fKb_lL-e-7G7UnnCcN1Ea6/view?usp=drive_link)

## Quickstart
You can test it by running the scripts in the root folder to convert audio to both summary or report. Lets assume you downloaded the [sample audio file from google drive](https://drive.google.com/file/d/1Y_76o_JHO1fKb_lL-e-7G7UnnCcN1Ea6/view?usp=drive_link) and placed it in the **Downloads** folder.

### Generating summary from audio
```bash
cd /path/to/this/repo
conda activate ai
python workflows/audio_to_summary.py --audio_file=/home/user/Downloads/secao_3.mpeg
```

### Generating report from audio

```bash
cd /path/to/this/repo
conda activate ai
python workflows/audio_to_report.py --audio_file=/home/user/Downloads/secao_3.mpeg
```

## Running the Interfaces
After creating and activating the conda environment, ensure Ollama service is running, then start the web interfaces using Streamlit.

### Audio-to-Text
```bash
cd /path/to/this/repo
streamlit run apps/report_app.py
```

This will launch a web interface where you can upload an audio file (in Portuguese) for transcription using our assistant model. Note that inference on CPU may be slower.

### Personalized Chatbot
```bash
cd /path/to/this/repo
streamlit run apps/chat_app.py
```

This will launch a web interface where you will see a chat prompt. The assistant will behave as a servant, treating you as its lord as in centuries ago. This is intentional to illustrate the possibility of adding personality to the assistant.

## Building the Docker image
### Chat app
Run the following command to pull and generate the customizes model we are going to use in the chat app. Make sure you have gone through the __prerequisites__ section and have the conda environment running.

```bash
conda activate ai
cd /path/to/this/repo
python workflows/create_custom_model.py
```

Copy your ollama customized and original models __blobs__ and __manifests__ folders to the **ollama_models** subfolder. This will guarantee they are placed in the Docker images we are building. The original ollama models folders are usually at __/usr/share/ollama/.ollama/models__. Make sure you are not copying extra blobs and manifests so that the docker image doesn't get too big.

Once you have [docker installed in your machine](https://docs.docker.com/engine/install/), you can create the images for your apps.

Run the following command to create the docker image:

```bash
cd /path/to/this/repo
docker build -f Dockerfile.chatapp -t chat-app:latest .
```

Or instead just **pull it from Dockerhub**:
```bash
docker pull viniciusfvidal/chat-app:latest
docker tag viniciusfvidal/chat-app:latest chat-app:latest
```

## Running the Docker image
### Chat app
To run the built images you should have nvidia-container-toolkit installed. Follow the commands to install it:

```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID) \
    && curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
    && curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker
```

To test the installation run the following command, where you should have the image pulled and your GPU data printed as the correct output:

```bash
docker run --rm --gpus all nvidia/cuda:12.2.2-base-ubuntu22.04 nvidia-smi
```

Use the following command to run the docker container on top of the image
```bash
docker run --gpus all --name chat-app --privileged -it -p 8501:8501 chat-app:latest
```
