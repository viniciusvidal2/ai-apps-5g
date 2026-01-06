import chromadb
from chromadb.utils import embedding_functions
from chromadb.api.models import Collection
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.chunking import HybridChunker


class DatabaseManager():
    def __init__(self, db_path: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=db_path)
        self.bge_m3_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="BAAI/bge-m3",
            device="cuda"
        )
        self.pipeline_options = PdfPipelineOptions()
        self.pipeline_options.do_table_structure = True
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=self.pipeline_options,
                )
            }
        )
        self.chunker = HybridChunker(max_tokens=1024)

    def add_document(self, collection_name: str, document_path: str) -> None:
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
        # Extract just the text from each chunk object
        final_texts = [chunk.text for chunk in chunks_iterator]
        # Metadatas and IDs
        document_name = self._get_document_name(document_path)
        metadatas = [{"document_name": document_name} for _ in final_texts]
        ids = [document_name + "_chunk_" +
               str(i) for i in range(len(final_texts))]
        collection.add(
            documents=final_texts,
            metadatas=metadatas,
            ids=ids
        )
        print(
            f"Added {len(final_texts)} chunks to collection '{collection_name}'.")

    def inspect_collection(self, collection_name: str):
        collection = self.client.get_or_create_collection(name=collection_name)
        print(
            f"Collection '{collection_name}' has {collection.count()} documents.")
        print(f"First 10 documents: {collection.peek()}")

    def query_collection(self, collection_name: str, query_text: str, n_results: int = 5):
        collection = self.client.get_or_create_collection(name=collection_name)
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        return results

    def _check_if_document_exists(self, collection: Collection, document: str) -> bool:
        # We only need to find 1 record to know the doc exists
        results = collection.get(
            where={"document_name": self._get_document_name(document)},
            limit=1,
            include=[]
        )
        return len(results['ids']) > 0

    def _get_document_name(self, document_path: str) -> str:
        if "/" not in document_path:
            return document_path
        return document_path.split("/")[-1]


if __name__ == "__main__":
    db_manager = DatabaseManager(
        db_path="./database_manager/chroma_db_testing")
    pdf_paths = ["/home/vini/Downloads/Hotel SP Setembro 2025.pdf"]
    for pdf_path in pdf_paths:
        db_manager.add_document(
            collection_name="my_collection", document_path=pdf_path)
    db_manager.inspect_collection(collection_name="my_collection")

    # Sample query
    query = "Qual o local do hotel?"
    results = db_manager.query_collection(
        collection_name="my_collection", query_text=query, n_results=3)
    for doc, score in zip(results['documents'][0], results['distances'][0]):
        print(f"Score: {score}\nDocument Chunk: {doc}\n")
