# Database Manager

This is the database manager folder, where we can:

- create a chromadb database
- build and run a docker image with the provided Dockerfile

## Creating a database

The first step you should perform to create the database is installing the script dependencies in your system (which you can do in root, but conda or virtual environment are recommended):

```bash
cd requirements
pip install -r requirements_chromadb.txt
```

You database should be described in a yaml file similar to the default one, __database_manager/database_description.yaml__ (or just change the values in this one). The file should be passed as an argument to the script alongside the database output path, which you will pass as a shared volume to the chromadb server docker container in the following sections.

The command to create the database (set the device according to your machine to 'cpu' or 'cuda', where 'cpu' is the default):

```bash
cd database_manager
python database_manager.py --db_path /your/chromadb/local/path --yaml_path /your/yaml/local/path --device 'cpu'
```

You should have the database fully vectorized in your system after a while o processing (which can take minutes depending on your documents).

## Building and running the image

You should build the image with the following command:

```bash
cd ai-apps-5g
docker build -t chroma_server -f dockerfiles/Dockerfile.chromadb .
```

We must have the remote chromadb server running to access it through HTTP client. To run the image we must make sure we pass port 8000 and the shared colume where we built our chroma database. The full command should be:

```bash
docker run --rm -d -v /your/chromadb/local/path:/app/chroma_db -p 8000:8000 --name chroma_server chroma_server:latest
```

Be aware that for restarting the command you should stop it before running it again, as chroma process can be persistent even after ctrl+c SIGINT signal is sent.

## Testing the database server

Wether you run the server manually or with the docker image, you should follow the example file in database_test_client.py to get it going. The following command should provide a logical feedback of the database access, given a sample query you know should be found in your documents, and other data to access database and server properly:

```bash
cd ai-apps-5g/database_manager
python database_test_client.py --query "your derired query" --collection "your_collection_name" --port 8000 --ip localhost
```
