# Rest APIs

This repository is meant for any rest APIs we use both for OCI integrations and local testing. The idea is to make a bridge between calling IHM and the agent dockers.

## Local testing - AI Assistant Agent

We must be able to start and stop the ai assistant agent docker using this REST API interface. Both endpoints (/start_docker and /kill_docker) are handled by a single service running on port 8002.

### Building the docker for the manager API

Run the following command to build the AI assistant manager docker:

```bash
cd ai_apps_5g
docker build -t ai-assistant-manager-api -f rest_apis/Dockerfile .
```

### Running the docker

The docker will deal with docker containers in the host machine. Use the following command to run the manager docker:

```bash
docker run --rm \
-p 8002:8002 \
-v /var/run/docker.sock:/var/run/docker.sock \
-v $(which docker):/usr/bin/docker \
--name ai-assistant-manager-api \
ai-assistant-manager-api:latest
```

### Requests examples

One can use the file __rest_apis/start_kill_tests.py__ to test the running docker. Both start and kill actions now target port 8002. To simply call the file, use the commands:

```bash
cd ai_apps_5g/rest_apis
python start_kill_tests.py --action [ACTION]  # 'start' or 'kill'
```

Inspect the code to better understand the data format we must provide to the REST APIs in order to perform both __start__ and __kill__ actions.
