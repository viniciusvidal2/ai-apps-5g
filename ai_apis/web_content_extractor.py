import requests
import trafilatura
from typing import Optional, Dict
import traceback
import chromadb
from chromadb.utils import embedding_functions
from chromadb.api.models import Collection
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from langchain.text_splitter import TokenTextSplitter


class WebContentExtractor:
    # region Constructor
    def __init__(self):
        """The WebContentExtractor constructor"""
        # The efemeral chromadb client can be used to cache embeddings
        self.client = chromadb.Client()
        self.ebf = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="Qwen/Qwen3-Embedding-0.6B",
            device="cuda"
        )
        # Text splitter to create chunks from the extracted text
        self.splitter = TokenTextSplitter(
            chunk_size=2048,
            chunk_overlap=200
        )
# endregion
# region Public Methods

    def query_content_from_url(self, url: str, query: str) -> str:
        """
        Extracts content from a URL, stores it in chromadb, and performs a similarity search with the given query.

        Args:
            url (str): The URL to extract content from.
            query (str): The query string to perform similarity search.

        Returns:
            str: The combined text of the most similar chunks.
        """
        # Get the textual content from the URL
        extracted = self.extract_content(url)
        text = extracted["content"]
        # Convert it into chunks and store in chromadb
        collection_name = f"{url.replace('/', '_').replace(':', '_')}"
        self._add_to_collection(collection_name, text, {"source": url})
        # Then perform a similarity search with the query to get relevant chunks
        return self._similarity_search(collection_name, query, top_k=2)

    def extract_content(self, url: str) -> Dict:
        """
        Extracts content from a URL based on its content type.

        Args:
            url (str): The URL to extract content from.

        Returns:
            Dict: A dictionary containing the extracted content and metadata.
        """
        content_type = self._get_content_type(url)

        if content_type is None:
            raise RuntimeError("Could not determine content type")

        if "text/html" in content_type:
            return self._extract_html(url)

        if "application/pdf" in content_type:
            return self._extract_pdf(url)

        raise NotImplementedError(
            f"Unsupported Content-Type: {content_type}"
        )

# endregion
# region Private Methods

    def _similarity_search(self, collection_name: str, query: str, top_k: int = 5) -> str:
        """
        Performs a similarity search in the specified collection using the given query.

        Args:
            collection_name (str): The name of the collection to search in.
            query (str): The query string to search for.
            top_k (int): The number of top similar results to retrieve.

        Returns:
            str: The combined text of the most similar chunks.
        """
        collection: Collection = self.client.get_collection(
            name=collection_name,
            embedding_function=self.ebf
        )
        results = collection.query(
            query_texts=[query],
            n_results=top_k
        )
        # Combine the top_k results into a single string
        combined_text = "\n\n".join(results['documents'][0])
        return combined_text

    def _add_to_collection(self, collection_name: str, text: str, metadata: Dict) -> None:
        """
        Adds text chunks to a specified collection in chromadb.

        Args:
            collection_name (str): The name of the collection to add to.
            text (str): The text to be chunked and added.
            metadata (Dict): Metadata to associate with each chunk.
        """
        collection: Collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.ebf
        )
        # Create chunks to add to the collection
        chunks = self.splitter.split_text(text)

        for i, chunk in enumerate(chunks):
            collection.add(
                documents=[chunk],
                metadatas=[{**metadata, "chunk_index": i}],
                ids=[f"{metadata.get('source', 'unknown')}_chunk_{i}"]
            )

    def _get_content_type(self, url: str) -> Optional[str]:
        """
        Gets the content type of the resource at the given URL.

        Args:
            url (str): The URL to check.

        Returns:
            Optional[str]: The content type if available, otherwise None.
        """
        try:
            r = requests.head(
                url,
                allow_redirects=True,
                timeout=15,
                headers={"User-Agent": "WebContentExtractor/1.0"},
            )
            return r.headers.get("Content-Type", "").lower()
        except requests.RequestException:
            return None

    def _extract_html(self, url: str) -> Dict:
        """
        Extracts and cleans HTML content from the given URL.

        Args:
            url (str): The URL to extract HTML content from.

        Returns:
            Dict: A dictionary containing the extracted content and metadata.
        """
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            raise RuntimeError("Failed to fetch HTML content")

        text = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
            include_links=False,
            include_images=False,
            output_format="markdown",
        )
        if not text:
            raise RuntimeError("Trafilatura failed to extract content")

        return {
            "source": url,
            "type": "html",
            "content": text,
        }

    def _extract_pdf(self, url: str) -> Dict:
        """
        Extracts text content from a PDF at the given URL.

        Args:
            url (str): The URL to extract PDF content from.

        Returns:
            Dict: A dictionary containing the extracted content and metadata.
        """
        # Configure Docling to convert PDF without extra processing
        options = PdfPipelineOptions(
            do_ocr=False,
            do_table_structure=False,
            generate_page_images=False,
            generate_picture_images=False,
            do_formula_enrichment=False,
        )
        pdf_format_options = PdfFormatOption(pipeline_options=options)
        converter = DocumentConverter(
            format_options={InputFormat.PDF: pdf_format_options}
        )
        # Perform the conversion
        try:
            result = converter.convert(source=url)
        except Exception as e:
            print("=== DOCLING PIPELINE FAILURE ===")
            traceback.print_exc()
            raise
        text = result.document.export_to_markdown()

        return {
            "source": url,
            "type": "pdf",
            "content": text,
        }
# endregion


if __name__ == "__main__":
    # Example usage
    extractor = WebContentExtractor()

    url = "https://arxiv.org/pdf/2601.00169"

    try:
        result = extractor.extract_content(url)
        print(f"Source: {result['source']}")
        print(f"Type: {result['type']}")
        query = "what is the introduction of this paper?"
        similar_section = extractor.query_content_from_url(url, query)
        # print("----- Similar Section -----")
        # print(f"\nQuery: {query}")
        # print(f"\n\nSimilar Section:\n{similar_section}")
    except Exception as e:
        print(f"Error: {e}")
