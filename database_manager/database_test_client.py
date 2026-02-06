import argparse
import chromadb
from chromadb.config import Settings
from httpx import ConnectError, ConnectTimeout


class DatabaseTestClient():
    def __init__(self, ip: str = "localhost", port: int = 8000):
        """
        Database test client class constructor

        Args:
            ip (str, optional): ChromaDB server IP address. Defaults to "localhost".
            port (int, optional): ChromaDB server port. Defaults to 8000.
        """
        self.ip_address = ip
        self.port = port

    def init_remote_client(self) -> bool:
        """
        Creates a ChromaDB HTTP client and tests the connection.

        Returns:
            bool: True if the connection is successful, False otherwise.
        """
        try:
            self.client = chromadb.HttpClient(
                host=self.ip_address,
                port=self.port,
                settings=Settings(
                    chroma_server_ssl_verify=False
                )
            )
            self.client.heartbeat()
            print(
                f"✅ Successfully connected to ChromaDB at {self.ip_address}:{self.port}")
            return True
        except (ConnectError, ConnectTimeout) as e:
            print(
                f"❌ Connection Failed: Could not reach ChromaDB at {self.ip_address}:{self.port}.")
            print(f"Internal Error: {e}")
            self.client = None
        except Exception as e:
            print(
                f"⚠️ An unexpected error occurred during initialization: {e}")
            self.client = None
        return False

    def list_collections(self) -> None:
        """Lists all collections in the ChromaDB client."""
        collections = self.client.list_collections()
        for collection in collections:
            print(f"Collection Name: {collection.name}, ID: {collection.id}")

    def query_collection(self, collection_name: str, query_text: str, n_results: int = 5) -> dict:
        """
        Queries the specified collection in the database.

        Args:
            collection_name (str): The name of the collection to query.
            query_text (str): The text to query against the collection.
            n_results (int, optional): Number of results to return. Defaults to 5.

        Returns:
            dict: The query results.
        """
        collection = self.client.get_or_create_collection(name=collection_name)
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        return results


def main() -> None:
    """Sample usage of the DatabaseTestClient to connect to ChromaDB."""
    parser = argparse.ArgumentParser(
        description="Test ChromaDB connection and query collections.")
    parser.add_argument(
        "--ip", "-i",
        type=str,
        default="localhost",
        help="ChromaDB server IP address (default: localhost)"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8000,
        help="ChromaDB server port (default: 8000)"
    )
    parser.add_argument(
        "--collection", "-c",
        type=str,
        default="my_collection",
        help="Name of the collection to query (default: my_collection)"
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        default="Sample query text",
        help="Text to query against the collection (default: 'Sample query text')"
    )
    args = parser.parse_args()

    db_test_client = DatabaseTestClient(ip=args.ip, port=args.port)
    if not db_test_client.init_remote_client():
        return
    db_test_client.list_collections()

    # Sample query
    results = db_test_client.query_collection(
        collection_name=args.collection, query_text=args.query, n_results=3)
    for doc, score in zip(results['documents'][0], results['distances'][0]):
        print(f"Score: {score:.4f}, Document: {doc}")


if __name__ == "__main__":
    main()
