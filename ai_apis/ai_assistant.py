from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_ollama import ChatOllama
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from typing import Dict, Any, List
import os


class AiAssistant:
    # region Initialization and Setup
    """
    Manages a RAG (Retrieval-Augmented Generation) database using Chroma and Ollama models.
    """

    def __init__(self, embedding_model_name: str, inference_model_name: str, persist_path: str, collection_name: str) -> None:
        """
        Initializes the RAG Database Manager with the specified models and database path.

        Args:
            embedding_model_name (str): The name of the Ollama embedding model to use.
            inference_model_name (str): The name of the Ollama inference model to use.
            persist_path (str): The directory path where the Chroma database will be stored.
            collection_name (str): The name of the collection within the Chroma database.
        """
        self.embedding_model_name = embedding_model_name
        self.inference_model_name = inference_model_name
        self.persist_path = persist_path
        self.collection_name = collection_name
        self.embedding_function = OllamaEmbeddings(
            model=self.embedding_model_name)
        self.vectorstore = self._load_or_initialize_db()
        # This assumes you have the model pulled and Ollama is running
        self.llm = ChatOllama(model=self.inference_model_name)
        # Initialize the prompt templates
        DOCUMENT_PROMPT_TEMPLATE = """
        --- CHUNK DE CONTEXTO ---
        Fonte: {source} (Pagina {page})
        CONTEUDO:
        {page_content}
        --------------------
        """
        self.document_prompt = PromptTemplate.from_template(
            DOCUMENT_PROMPT_TEMPLATE)
        self.rag_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "Voce e um assistente de IA que ajuda a responder perguntas com base no CONTEXTO fornecido, "
             "mas tambem pode usar seu conhecimento geral. Cada CHUNK DE CONTEXTO e um trecho de um CONTEUDO de documento que pode conter informaçoes relevantes. "
             "Voce deve sempre retornar a fonte e a pagina de cada CHUNK DE CONTEXTO que voce usou para construir sua resposta. \n"
             "CONTEXTO:\n{context}"),
            ("human", "{input}"),
        ])
        self.message_history = []

# endregion
# region Private internal methods

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

# endregion
# region Database RAG methods

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
        # Check if the document was already added to the database
        if self.vectorstore:
            existing_docs = self.vectorstore.similarity_search(
                query=source_name, k=1)
            if existing_docs:
                print(
                    f"Document '{source_name}' already exists in the database. Skipping addition.")
                return
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
                "source": source_name,  # Overwrite the 'source' path if PyPDFLoader set a full path
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
            self.vectorstore.persist()
            print(
                f"Successfully added {len(document_chunks)} chunks to the database.")
        else:
            print("Document was empty or too short to chunk.")

    def build_rag_prompt(self, query: str, n_chunks: int = 5) -> Dict[str, Any]:
        """
        Retrieves documents from the vectorstore and builds the final RAG prompt.

        Args:
            query (str): The user's input query.
            n_chunks (int): The number of context chunks to retrieve (default 5).

        Returns:
            Dict[str, Any]: Contains the final prompt string, retrieved docs, and context string.
        """
        if not self.vectorstore:
            return {"prompt": None, "context_documents": [], "context_string": ""}

        retriever = self.vectorstore.as_retriever(
            search_kwargs={"k": n_chunks})
        retrieved_docs = retriever.invoke(query)

        # Format retrieved docs into context
        formatted_context_chunks = [
            self.document_prompt.format(
                page_content=doc.page_content,
                source=doc.metadata.get("source", "Unknown"),
                page=doc.metadata.get("page", "N/A"),
            )
            for doc in retrieved_docs
        ]
        context_string = "\n".join(formatted_context_chunks)

        # Fill the RAG prompt
        final_prompt_value = self.rag_prompt.format_prompt(
            context=context_string,
            input=query,
        )
        final_prompt_string = final_prompt_value.to_string()

        # # Debug print
        # print("\n" + "=" * 50)
        # print("🌟 FINAL PROMPT BUILT 🌟")
        # print(final_prompt_string)
        # print("=" * 50 + "\n")

        return {
            # This is a PromptValue object (LangChain)
            "prompt": final_prompt_value,
            "prompt_string": final_prompt_string,
            "context_documents": retrieved_docs,
            "context_string": context_string,
        }

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

        # Create the Document Chain (combines retrieved docs and prompt into a single message for the LLM)
        document_chain = create_stuff_documents_chain(
            self.llm,
            self.rag_prompt,
            # This applies the DOCUMENT_PROMPT to each document
            document_prompt=self.document_prompt
        )

        # Create the Retrieval Chain (combines the retriever and the document chain)
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})
        # -----------------------------------------------------------------------
        retrieved_docs = retriever.invoke(query)
        # Create the context string using the document_prompt for each retrieved doc
        formatted_context_chunks = [
            self.document_prompt.format(
                page_content=doc.page_content,
                source=doc.metadata.get('source', 'Unknown'),
                page=doc.metadata.get('page', 'N/A')
            )
            for doc in retrieved_docs
        ]
        context_string = "\n".join(formatted_context_chunks)
        # Now, fill the RAG prompt with the context and the query
        final_prompt_value = self.rag_prompt.format_prompt(
            context=context_string,
            input=query
        )
        # 🌟 PRINT THE FINAL PROMPT HERE 🌟
        print("\n" + "="*50)
        print("🌟 FINAL PROMPT SENT TO LLM 🌟")
        # This prints the prompt in the format the LLM expects (System/User messages)
        print(final_prompt_value.to_string())
        print("="*50 + "\n")
        # -----------------------------------------------------------------------
        retrieval_chain = create_retrieval_chain(retriever, document_chain)

        # Invoke the Chain
        print(f"\n--- Running RAG Chain with {self.inference_model_name} ---")
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

# endregion
# region Inference related methods

    def format_general_user_prompt(self, user_input: str) -> str:
        """
        Formats a general user input into the RAG prompt structure without retrieval.

        Args:
            user_input (str): The user's input query.

        Returns:
            str: The formatted prompt string.
        """
        final_prompt_value = self.rag_prompt.format_prompt(
            context="Nenhum contexto fornecido, utilize seu conhecimento ou o histórico de mensagens anteriores.",
            input=user_input,
        )
        final_prompt_string = final_prompt_value.to_string()

        # Debug print
        print("\n" + "=" * 50)
        print("🌟 FORMATTED USER PROMPT 🌟")
        print(final_prompt_string)
        print("=" * 50 + "\n")

        return final_prompt_string

    def run_inference(self, prompt: Any) -> Dict[str, Any]:
        """
        Runs inference on a given prompt using the LLM.
        Can take either a string or a LangChain PromptValue.

        Args:
            prompt (str | PromptValue): The prepared prompt.

        Returns:
            Dict[str, Any]: The model's answer.
        """
        # If string, wrap into the right input format
        if isinstance(prompt, str):
            input_data = {"input": prompt}
        else:
            input_data = {"input": prompt.to_string()}

        response = self.llm.invoke(input_data["input"])  # direct LLM call

        return {
            "answer": response.content,
        }

# endregion
# region Message History methods

    def increment_history(self, user_input: str, assistant_response: str) -> None:
        """
        Updates the message history with a new user input and assistant response.

        Args:
            user_input (str): The user's input message.
            assistant_response (str): The assistant's response message.
        """
        self.message_history += [
            {'role': 'user', 'content': user_input},
            {'role': 'assistant', 'content': assistant_response},
        ]

    def clear_history(self) -> None:
        """
        Clears the message history.
        """
        self.message_history = []

    def get_history(self) -> List[Dict[str, str]]:
        """
        Returns the current message history.

        Returns:
            List[Dict[str, str]]: The message history.
        """
        return self.message_history

# endregion
# region Example usage


if __name__ == "__main__":
    # List of PDFs to add to the database
    pdf_files = [
        # "/home/vini/Downloads/Passagem - SP - Setembro.pdf",
        # "/home/vini/Downloads/Hotel SP Setembro 2025.pdf",
        # "/home/vini/Downloads/box 31 servicos.pdf",
        # "/home/vini/Downloads/contrato natal.pdf",
        # "/home/vini/Downloads/Relatório_de_Atividades___Integração_de_Dados.pdf",
        "/home/vini/Downloads/APEX and SOLIX G3 Operations Manual.pdf"
    ]

    # Model to be used
    embedding_model_name = "qwen3-embedding:latest"
    inference_model_name = "gpt-oss:120b"

    # Initialize the RAG Database Manager
    print("Initializing RAG Database Manager...")
    ai_assistant = AiAssistant(
        embedding_model_name=embedding_model_name,
        inference_model_name=inference_model_name,
        persist_path="./chroma_db",
        collection_name="initial_database"
    )

    # Add each PDF to the database
    MAX_CHUNK_SIZE = 128000
    N_CHUNKS = 10  
    CHUNK_SIZE = MAX_CHUNK_SIZE // N_CHUNKS  
    for pdf_file in pdf_files:
        # Add the PDF content to the RAG database
        ai_assistant.add_document_to_db(
            document_path=pdf_file,
            chunk_size=CHUNK_SIZE,
            chunk_overlap=200,
            source_name=os.path.basename(pdf_file)
        )

    # Generate an answer to a query
    querys = [
        # "Qual é o código da minha reserva nesta passagem aérea?",
        # "Qual o nome do hotel onde ficarei hospedado?",
        # "Qual o valor total gasto com a passagem aerea do rio de janeiro para sao paulo?",
        # "Qual meu endereço completo em Parnamirim",
        "Há a possibilidade de obter dados em tempo real do APEX 16 utilizando alguma porta NMEA?",
    ]
    for query in querys:
        print("\n" + "-" * 80)
        print(f"--- Running Inference with {inference_model_name} ---")
        rag_prompt = ai_assistant.build_rag_prompt(query=query, n_chunks=N_CHUNKS)
        response = ai_assistant.run_inference(
            prompt=rag_prompt["prompt_string"])
        print(f"QUERY: {query}")
        print(f"ANSWER: {response['answer']}")
        print("SOURCES:")
        for doc in rag_prompt["context_documents"]:
            print(
                f"- {doc.metadata.get('source', 'Unknown')}, (Page {doc.metadata.get('page', 'N/A')})")
        print("-" * 80)
# endregion
