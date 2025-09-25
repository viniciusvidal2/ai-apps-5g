from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.chat_models import ChatOllama
from langchain_community.document_loaders import PyPDFLoader
from langchain.schema.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from typing import Dict, Any
import os


class RagDatabaseManager:
    def __init__(self, model_name: str, persist_path: str, collection_name: str) -> None:
        self.model_name = model_name
        self.persist_path = persist_path
        self.collection_name = collection_name
        self.embedding_function = self._initialize_embeddings()
        self.vectorstore = self._load_or_initialize_db()
        print(f"Database Handler initialized.")
        print(f"Embedding Model: {self.model_name}")
        print(f"Persist Directory: {self.persist_path}")
        # This assumes you have the model pulled and Ollama is running
        self.llm = ChatOllama(model=self.model_name)
        # Initialize the prompt templates
        DOCUMENT_PROMPT_TEMPLATE = """
        --- CONTEXT CHUNK ---
        Source: {source} (Page {page})
        Content:
        {page_content}
        --------------------
        """
        self.document_prompt = PromptTemplate.from_template(DOCUMENT_PROMPT_TEMPLATE)
        self.rag_prompt = ChatPromptTemplate.from_messages([
            ("system",
            "Voce e um assistente de IA que ajuda a responder perguntas com base em documentos fornecidos, "
            "mas tambem pode usar seu conhecimento geral."
            "Contexto:\n{context}"),
            ("human", "{input}"),
        ])

# region Private internal methods

    def _initialize_embeddings(self) -> OllamaEmbeddings:
        """
        Initializes the Ollama Embeddings object.

        Returns:
            OllamaEmbeddings: The initialized embeddings object.
        """
        try:
            # Assumes Ollama is running and the model is pulled
            return OllamaEmbeddings(model=self.model_name)
        except Exception as e:
            print(f"Error initializing Ollama Embeddings. Ensure Ollama is running.")
            print(f"Details: {e}")
            raise

    def _load_or_initialize_db(self) -> Chroma:
        """
        Loads an existing DB or initializes an empty one if the path is empty/new.

        Returns:
            Chroma: The loaded or newly created Chroma vector store.
        """
        try:
            # Try to load existing database
            db = Chroma(
                persist_directory=self.persist_path,
                embedding_function=self.embedding_function,
                collection_name=self.collection_name
            )
            if db._collection.count() > 0:
                print(
                    f"✅ Existing database loaded with {db._collection.count()} items.")
            else:
                # Initialize an empty DB structure if the folder exists but is empty
                print(
                    "Database directory exists but is empty. Initializing new structure.")
            return db
        except Exception:
            # Create a new, empty Chroma instance for the first run
            print(
                f"Creating new Chroma database structure at {self.persist_path}.")
            return Chroma(
                embedding_function=self.embedding_function,
                collection_name=self.collection_name,
                persist_directory=self.persist_path
            )

    def _persist_db(self) -> None:
        """Helper to ensure persistence is called."""
        if self.vectorstore:
            self.vectorstore.persist()
            print("✅ Database successfully persisted to disk.")
        else:
            print("Error: Vector store is not initialized.")

    def _as_retriever(self, search_kwargs: dict = {"k": 5}) -> Any:
        """
        Returns a LangChain Retriever object for performing similarity searches.

        Args:
            search_kwargs (dict): Parameters for the retriever, e.g., number of results to return.

        Returns:    
            Any: A LangChain Retriever object or None if the vectorstore is not initialized.
        """
        if self.vectorstore:
            return self.vectorstore.as_retriever(search_kwargs=search_kwargs)
        return None

# endregion
# region Public methods

    def add_document_to_db(self, document_path: str, chunk_size: int, chunk_overlap: int = 200, source_name: str = "doc_file") -> None:
        """
        Takes a raw document string, chunks it, and adds the chunks to the vector database.

        Args:
            document_path (str): The file path to the document to be added.
            chunk_size (int): The maximum number of characters in each chunk.
            chunk_overlap (int): The number of characters to overlap between chunks (default 200).
            source_name (str): A name/identifier for the document to use in the metadata.
        """
        print(f"\n--- Adding Document: {source_name} ---")
        # Load the document using PyPDFLoader
        loader = PyPDFLoader(document_path)
        pages = loader.load()  # Pages are returned as a list of Document objects
        # Initialize Text Splitter
        text_splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", " ", ""],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        # Convert text chunks to LangChain Document objects and add metadata
        document_chunks = text_splitter.split_documents(pages)

        # Enhance Metadata for easier tracking (Optional but helpful)
        # The chunking process already created LangChain Document objects, 
        # but we can iterate to add a 'full_source' and 'chunk_index' field.
        for i, chunk in enumerate(document_chunks):
            page_info = f"Page: {chunk.metadata.get('page', 'N/A')}"
            chunk.metadata.update({
                "source": source_name, # Overwrite the 'source' path if PyPDFLoader set a full path
                "chunk_index": i,
                "full_source": f"File: {source_name}, {page_info}, Chunk: {i}"
            })
            # Clean up any potential extra metadata from the loader if necessary (e.g., total_pages)
            if 'total_pages' in chunk.metadata:
                del chunk.metadata['total_pages']
        
        # Add documents to the Vector Store and Persist
        if document_chunks:
            print(
                f"Generated {len(document_chunks)} chunks of size up to {chunk_size}.")

            # Use Chroma's add_documents method to insert and embed the chunks
            self.vectorstore.add_documents(documents=document_chunks)

            # Persist the changes to disk
            self._persist_db()
            print(
                f"Successfully added {len(document_chunks)} chunks to the database.")
        else:
            print("Document was empty or too short to chunk.")

    def generate_rag_answer(self, query: str) -> Dict[str, Any]:
        """
        Runs the RAG chain: retrieves context and generates an answer using an LLM.

        Args:
            query (str): The user's question.

        Returns:
            Dict[str, Any]: A dictionary containing the final answer and the source documents.
        """
        if not self.vectorstore:
            print("Error: Vector database is not initialized. Cannot run RAG chain.")
            return {"answer": "Database not available.", "context": []}

        # 2. Create the Document Chain (combines retrieved docs and prompt into a single message for the LLM)
        # 🌟 KEY CHANGE: Pass the DOCUMENT_PROMPT to the chain configuration.
        # This ensures each retrieved Document is formatted using this prompt template
        # before being combined into the large '{context}' block of the RAG_PROMPT_TEMPLATE.
        document_chain = create_stuff_documents_chain(
            self.llm, 
            self.rag_prompt, 
            document_prompt=self.document_prompt  # <--- This applies the DOCUMENT_PROMPT to each document
        )

        # 3. Create the Retrieval Chain (combines the retriever and the document chain)
        retriever = self._as_retriever(
            search_kwargs={"k": 5})  # Retrieve top 5 chunks
        retrieval_chain = create_retrieval_chain(retriever, document_chain)

        # 4. Invoke the Chain
        # 🌟 KEY CHANGE: The RAG_PROMPT_TEMPLATE is automatically used here because 
        # it was passed into the document_chain, which is part of the retrieval_chain.
        print(f"\n--- Running RAG Chain with {self.model_name} ---")
        response = retrieval_chain.invoke({"input": query})

        # Format the context for better display
        context_sources = [
            f"Source: {doc.metadata.get('full_source', doc.metadata.get('source', 'Unknown'))}\nContent: {doc.page_content[:150]}..." for doc in response["context"]]

        print("✅ RAG Answer Generated.")
        return {
            "answer": response["answer"],
            "context_documents": response["context"],
            "sources_summary": "\n".join(context_sources)
        }

    def get_database_path(self) -> str:
        """Returns the path to the RAG database.

        Returns:
            str: The path to the RAG database.
        """
        return self.persist_path

# endregion
# region Example usage


if __name__ == "__main__":
    # List of PDFs to add to the database
    pdf_files = [
        "/home/vini/Downloads/Passagem - SP - Setembro.pdf",
        "/home/vini/Downloads/Hotel SP Setembro 2025.pdf",
        "/home/vini/Downloads/box 31 servicos.pdf",
        "/home/vini/Downloads/contrato natal.pdf",
        "/home/vini/Downloads/Relatório_de_Atividades___Integração_de_Dados.pdf",
    ]

    # Model to be used
    model_name = "qwen3:14b"

    # Initialize the RAG Database Manager
    print("Initializing RAG Database Manager...")
    rag_manager = RagDatabaseManager(
        model_name=model_name,
        persist_path="./chroma_db",
        collection_name="initial_database"
    )

    # Add each PDF to the database
    for pdf_file in pdf_files:
        # Add the PDF content to the RAG database
        rag_manager.add_document_to_db(
            document_path=pdf_file,
            chunk_size=50000,
            chunk_overlap=200,
            source_name=os.path.basename(pdf_file)
        )

    # Generate an answer to a query
    querys = [
        "Qual é o código da minha reserva nesta passagem aérea?",
        "Qual o nome do hotel onde ficarei hospedado?",
        "Qual o valor total gasto com a passagem aerea do rio de janeiro para sao paulo?",
        "Qual meu endereço completo em Parnamirim"
    ]
    for query in querys:
        result = rag_manager.generate_rag_answer(
            query=query,
            llm_model=model_name
        )
        print(f"\n--- Query: {query} ---")
        print("Answer:", result["answer"].split("</think>")[-1])
        print("Context documents retrieved:", result["context_documents"])
# endregion
