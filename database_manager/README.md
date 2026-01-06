# Database Manager

This is the database manager folder, where we can:

- create a chromadb database
- build and run a docker image with the provided Dockerfile

## Creating a database


## Building and running the image

You should build the image with the following command:

```bash
cd ai-apps-5g/database_manager
docker build -t chroma_server .
```

We must have the remote chromadb server running to access it through HTTP client. To run the image we must make sure we pass port 8000 and the shared colume where we built our chroma database. The full command should be:

```bash
docker run --rm -d -v /your/chromadb/local/path:/app/chroma_db -p 8000:8000 --name chroma_server chroma_server:latest
```

Be aware that for restarting the command you should stop it before running it again, as chroma process can be persistent even after ctrl+c SIGINT signal is sent.

## Acessing the database server

Wether you run the server manually or with the docker image, you should follow the example file in database_test_client.py to get it going. The following command should provide a logical feedback of the database access, given a sample query you know should be found in your documents, and other data to access database and server properly:

```bash
cd ai-apps-5g/database_manager
python database_test_client.py --query "your derired query" --collection "your_collection_name" --port 8000 --ip localhost
```
