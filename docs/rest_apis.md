# Rest APIs

This repository is meant for any rest APIs we use both for OCI integrations and local testing. The idea is to make a bridge between calling IHM and the agent dockers.

## Local testing - AI Assistant Agent

We must be able to start and stop the ai assistant agent docker using this REST API interface. It will be just an endpoint for the IHM code to reach. The instruction will cover both dockers, which share ports with the host machine (8002 and 8003).

### Building de dockers for the APIs

Run the following commands to build the start ai assistant agent docker:

```bash
cd ai_apps_5g
docker build -t start-docker-rest-api -f rest_apis/Dockerfile.startaiassistantdocker .
```

Run the following commands to build the kill ai assistant agent docker:

```bash
cd ai_apps_5g
docker build -t kill-docker-rest-api -f rest_apis/Dockerfile.killaiassistantdocker .
```

### Running the dockers

The dockers will deal with docker containers in the host machine. Use the following command to run the start docker:

```bash
docker run --rm \
-p 8002:8002 \
-v /var/run/docker.sock:/var/run/docker.sock \
-v $(which docker):/usr/bin/docker \
--name start-docker-rest-api \
start-docker-rest-api:latest
```

For the kill docker:

```bash
docker run --rm \
-p 8003:8003 \
-v /var/run/docker.sock:/var/run/docker.sock \
-v $(which docker):/usr/bin/docker \
--name kill-docker-rest-api \
kill-docker-rest-api:latest
```

### Requests examples

One can use the file __rest_apis/start_kill_tests.py__ to test the running dockers. You should be able to launch the ai assistant agent docker from the image you have already built in your machine. To simply call the file, use the commands:

```bash
cd ai_apps_5g/rest_apis
python start_kill_tests.py --action [ACTION]  # 'start' or 'kill'
```

Inspect the code to better understand the data format we must provide to the REST APIs in order to perform both __start__ and __kill__ actions.
