import chromadb
from chromadb.utils import embedding_functions
from chromadb.api.models import Collection
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.chunking import HybridChunker
import yaml
import os
import argparse


class DatabaseManager():
    def __init__(self, db_path: str = "./chroma_db") -> None:
        """
        Database manager class constructor

        Args:
            db_path (str, optional): Database path. Defaults to "./chroma_db".
        """
        self.client = chromadb.PersistentClient(path=db_path)
        self.bge_m3_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="BAAI/bge-m3",
            device="cuda"
        )
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_table_structure = True
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                )
            }
        )
        self.chunker = HybridChunker(max_tokens=1024)

    def add_document(self, collection_name: str, document_path: str) -> None:
        """
        Adds a document to the specified collection in the database.

        Args:
            collection_name (str): The name of the collection to add the document to.
            document_path (str): The file path of the document to be added.
        """
        # Get the collection we are interested in
        collection = self.client.get_or_create_collection(name=collection_name)
        # Check if document already exists in collection
        if self._check_if_document_exists(collection, document_path):
            print(
                f"Document '{self._get_document_name(document_path)}' already exists in collection '{collection_name}'. Skipping.")
            return
        # Convert PDF to Docling's internal structured format
        result = self.converter.convert(document_path)
        chunks_iterator = self.chunker.chunk(dl_doc=result.document)
        # Prepare data for insertion
        final_texts = []
        metadatas = []
        ids = []
        document_name = self._get_document_name(document_path)
        for i, chunk in enumerate(chunks_iterator):
            final_texts.append(chunk.text)
            page_numbers = sorted(list(set(
                prov.page_no for item in chunk.meta.doc_items for prov in item.prov if hasattr(prov, "page_no")
            )))
            # Create metadata and id for this specific chunk
            metadatas.append({
                "document_name": document_name,
                # Chroma prefers strings or simple types
                "page_number": str(page_numbers)
            })
            ids.append(f"{document_name}_chunk_{i}")
        # Add to collection
        collection.add(
            documents=final_texts,
            metadatas=metadatas,
            ids=ids
        )
        print(
            f"Added {len(final_texts)} chunks to collection '{collection_name}'.")

    def inspect_collection(self, collection_name: str) -> None:
        """
        Inspects the specified collection in the database.

        Args:
            collection_name (str): The name of the collection to inspect.
        """
        collection = self.client.get_or_create_collection(name=collection_name)
        print(
            f"Collection '{collection_name}' has {collection.count()} documents.")
        print(f"First 10 documents: {collection.peek()}")

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

    def _check_if_document_exists(self, collection: Collection, document: str) -> bool:
        """
        Checks if a document already exists in the specified collection.

        Args:
            collection (Collection): The ChromaDB collection to check.
            document (str): The file path of the document to check.

        Returns:
            bool: True if the document exists, False otherwise.
        """
        # We only need to find 1 record to know the doc exists
        results = collection.get(
            where={"document_name": self._get_document_name(document)},
            limit=1,
            include=[]
        )
        return len(results['ids']) > 0

    def _get_document_name(self, document_path: str) -> str:
        """
        Extracts the document name from the full file path.

        Args:
            document_path (str): The full file path of the document.

        Returns:
            str: The extracted document name.
        """
        if "/" not in document_path:
            return document_path
        return document_path.split("/")[-1]


def create_database() -> None:
    """Creates and populates the database with given data from the description in the proper output folder."""
    # Get the current script path
    current_script_path = os.path.dirname(os.path.abspath(__file__))
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Database Manager for ChromaDB")
    parser.add_argument(
        "--db_path", "-d",
        type=str,
        default=os.path.join(current_script_path, 'chroma_db'),
        help="Path to the ChromaDB database (default: ./chroma_db)"
    )
    parser.add_argument(
        "--yaml_path", "-y",
        type=str,
        default=os.path.join(current_script_path, 'database_description.yaml'),
        help="Path to the database description YAML file (default: ./database_description.yaml)"
    )
    args = parser.parse_args()
    
    # Initialize DatabaseManager
    db_manager = DatabaseManager(
        db_path=args.db_path)
    # Load database description from YAML file
    with open(args.yaml_path, "r") as file:
        database_description = yaml.safe_load(file)
    # Add documents to collections as per the description
    for collection_name, collection_data in database_description.get("collections", {}).items():
        for document_path in collection_data.get("documents", []):
            db_manager.add_document(
                collection_name=collection_name, document_path=document_path)
    # Inspect one of the collections
    db_manager.inspect_collection(collection_name="my_collection")


if __name__ == "__main__":
    create_database()
