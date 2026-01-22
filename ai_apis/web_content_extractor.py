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
    def __init__(self):
        # The efemeral chromadb client can be used to cache embeddings if needed
        self.client = chromadb.Client()
        self.ebf = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="Qwen/Qwen3-Embedding-0.6B",
            device="cuda"
        )
        self.splitter = TokenTextSplitter(
            chunk_size=2048,
            chunk_overlap=200
        )

    def query_content_from_url(self, url: str, query: str) -> str:
        # Get the textual content from the URL
        extracted = self.extract_content(url)
        text = extracted["content"]
        # Convert it into chunks and store in chromadb
        collection_name = f"{url.replace('/', '_').replace(':', '_')}"
        self._add_to_collection(collection_name, text, {"source": url})
        # Then perform a similarity search with the query to get relevant chunks
        return self._similarity_search(collection_name, query, top_k=2)

    def _similarity_search(self, collection_name: str, query: str, top_k: int = 5) -> str:
        collection: Collection = self.client.get_collection(
            name=collection_name,
            embedding_function=self.ebf
        )
        results = collection.query(
            query_texts=[query],
            n_results=top_k
        )
        # Print every chunk retrieved
        for i, doc in enumerate(results['documents'][0]):
            print(f"--- Chunk {i+1} ---")
            print(doc)
            print("\n\n\n")
        # Combine the top_k results into a single string
        combined_text = "\n\n".join(results['documents'][0])
        return combined_text

    def _add_to_collection(self, collection_name: str, text: str, metadata: Dict):
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

    def extract_content(self, url: str) -> Dict:
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

    def _get_content_type(self, url: str) -> Optional[str]:
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
