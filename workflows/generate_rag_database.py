import os
import yaml
from ai_apis.ai_assistant import AiAssistant


def main() -> None:
    """Generates a database from given PDFs and URLs parsed from the config yaml file"""
    ############ Object creation and setup ############
    print("Initializing AI Assistant...")
    ai_assistant = AiAssistant(
        embedding_model_name="qwen3-embedding:0.6b",
        inference_model_name="gemma3:27b",
        documents_db_path="./dbs/chroma_documents_db",
        url_db_path="./dbs/chroma_url_db",
        collection_name="dev_collection"
    )
    ai_assistant.set_chunking_parameters(
        chunk_size=5000, chunk_overlap=200)

    ############ Database formation ############
    # Load PDFs and URLs from configuration file
    with open("workflows/config/database_inputs.yaml", "r") as config_file:
        config = yaml.safe_load(config_file)
    pdf_files = config.get("pdfs", [])
    urls = config.get("urls", [])

    ############ Adding documents to the database ############
    for pdf_file in pdf_files:
        print(f"Processing PDF: {pdf_file}")
        # Add the PDF content to the RAG database
        ai_assistant.add_document_to_db(
            document_path=pdf_file,
            source_name=os.path.basename(pdf_file)
        )

    ############ Adding URLs to search ############
    ai_assistant.reset_urls_to_search()
    ai_assistant.add_urls_to_search(urls=urls)
    print(f"Added {len(urls)} URLs to the web-based search list.")
    ai_assistant.create_database_from_urls()

    print("\n-- RAG database generation completed. --")


if __name__ == "__main__":
    main()
