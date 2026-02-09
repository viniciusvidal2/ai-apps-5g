# AI Assistant Agent

We will cover the basic working principles for the AI assistant agent, and how to build and run it. To run the database server and perform inference on documents, please refer to the __chromadb_server_setup.md__ file for instructions.

## Working concept

The agent uses ollama and langchain to return answers to the user queries. It can also perform RAG in a database, provided as a server outside the docker, that the user needs the context to have some search done. The database ip must be provided as a parameter so we can connect to it.

The communication between user and agent is performed through a REST API, and its port must be passed when running the agent container. We default to 8001.

We also must set the model we intend to use in the agent when running it, but it can also be swapped during execution.

## Installing the environment

Create a virtual environment of your preference and run the following commands to install the libraries:

```bash
cd ai_apps_5g
pip install -r requirements/ai_assistant.py
```

## Setting ollama models

The LLM models will reside inside the docker image for now, and are pulled when building the image itself. The command should include the desired models that one must pull. In the current version, __gemma3:4b__ is mandatory. These are the models we can use in our application (tested so far):

- gemma3:4b
- gemma3:12b
- gemma3:27b
- nemotron-3-nano:30b
- glm-4.7-flash:q8_0

You can find more models in [ollama library website link](https://ollama.com/library).

## Building the docker image

Use the following command to build the image. __gemma3:4b__ is mandatory, but you can add as many as you like from the list above:

```bash
docker build -t ai_assistant_image -f ai_assistant/Dockerfile --build-arg OLLAMA_MODELS_TO_PULL="gemma3:4b OTHER_MODELS" .
```

## Running the docker container

Use the following command to run the docker container from the built image.

```bash
docker run --rm -d -p 8001:8001 --name ai_assistant_agent ai_assistant_image --port=8001 --db_ip_address=DB_IP_ADDRESS --inference_model_name "[YOUR_MODEL_NAME]"
```

The docker runs in detached mode and is ready to exchange information. Remove the "-d" option flag if you want to see the debug prints.

## Verifying

Use the agent test script to check if the agent is properly responding. The test will reach the endpoint created by the agent REST API inside the running docker container:

```bash
cd ai_apps_5g/ai_assistant
python ai_assistant_agent_test.py --base-url "http://127.0.0.1:8001"
```

Several calls will be made to reach the api endpoints. You will see answers and other modules. This print should appear at the end, indicating everything was correct:

```bash
All tests passed ✅
```
