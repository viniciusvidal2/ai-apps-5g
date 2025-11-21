# AI Assistant Agent

We will cover the basic working principles for the AI assistant agent, and how to build and run it. Some dependencies are also covered regarding the vectorized database one must generate in order to have the assistant informed of specific content to perform RAG.

## Working concept

The agent uses ollama and laggraph to return answers to the user queries. It can also perform RAG in a database, created and copied to the docker, that the user needs the context to have some search done.

The communication between user and agent is performed through MQTT, so a broker must be active, and its information (IP and PORT) must be passed when running the agent container.

Finally, some arguments can be passed in the MQTT topic pyload to improve the agent performance:

- __search_db__: whether to use the given PDF documents database or not
- __search_urls__: whether to use the given fetched URLs database or not
- __use_history__: if we should use the conversation history in the current query or not; can give faster performance and reduce tokens, which avoids allucinations
- __n_chunks__: the ammount of database matches we will use to perform RAG; balance between fast and accurate versus slow, but broader knowledge in the answer. Ranges from 1 to 10.

## Installing the environment

Some python dependencies are needed to run several commands, involving database generation and agent testing, for example. Create a virtual environment of your preference and run the following commands to install them:

```bash
cd ai_apps_5g
pip install -r requirements/requirements_ai_assistant.py
```

## Generating the database

The database should reside in the __dbs__ folder, located in the root folder (if you don't have one already, please create so to be safe). There will be one for PDF files (chroma_documents_db), and another one for URLs (chroma_url_db).

Using the workflow that creates the database should be enough to vectorize your desired documents and URLs. Follow the instructions

### Setting the data

Go to __workflows/config/database_inputs.yaml__ and fill in your desired PDFs and URLs. They should follow the existing pattern to be read as lists.

### Calling the python module

Once the config file is done, run the command to generate your database in the proper format:

```bash
cd ai_apps_5g
python -m workflows.generate_rag_database
```

The __dbs__ folder should be now filled in your root directory, and your can now build the docker image or run the agent locally using RAG.

## Setting ollama models

Read the instructions in the __ollama_models__ folder on how to properly place the models, as of the ollama standard.

You should install ollama and pull models according to the [official website](https://ollama.com/). They are stored in you local ollama directory. Copy them to __ollama_models__ so we can insert them in the docker image.

The mandatory model to deal with embedding is __qwen3-embedding__. You should pull it from ollama website.

The currently supported models for inference are:

- gemma3:27b
- gemma3:12b
- gemma3:4b

For a quick and dirty test, use [this google drive link](https://drive.google.com/file/d/1MO-R0tJ2aTWDEf4gy12njLsZlOtIKbJD/view?usp=sharing) to download the zipped __gemma3:4b__ plus __qwen3-embedding__, and unzip it inside the __ollama_models__ folder.

## Building the docker image

We must have the dependencies set to build the image:

- A generated database inside the __dbs__ folder
- Ollama models properly placed inside the __ollama_models__ folder (all models will go inside the docker image so we can select them in runtime)

Use the following command to build the image:

```bash
docker build -t ai_assistant_image -f dockerfiles/Dockerfile.aiassistantagent .
```

## Running the docker container

Use the following command to run the docker container from the built image. __This command assumes you have a MQTT brocker running in your host machine, so it can connect to it and start exchanging messages.__

```bash
docker run --rm -d --network=host --name ai_assistant_agent ai_assistant_image --broker=0.0.0.0 --port=1883 --user_id=1 --input_topic=input --output_topic=output --inference_model_name "[YOUR_MODEL_NAME]"
```

The currently supported models for inference are:

- gemma3:27b
- gemma3:12b
- gemma3:4b

The docker runs in detached mode and is ready to exchange information.

## Verifying

Use the agent test script to check if the agent is properly responding. To run the basic test __(again, make sure MQTT broker is running and active to exchange messages with the agent docker)__, do the following in a terminal:

```bash
cd ai_apps_5g
python -m agents.ai_assistant_agent_test
```

It should take some time to run, but eventually you will see the response to a simple "Hello"-like message. No database or URLs are used in this example.
