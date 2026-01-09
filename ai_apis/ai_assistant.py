from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.prompts.chat import ChatPromptValue
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain.schema import SystemMessage, HumanMessage, AIMessage
import tiktoken
from typing import Dict, Any, List
import os
import subprocess


class AiAssistant:
    # region Initialization and Setup
    """
    Manages a RAG (Retrieval-Augmented Generation) database using Chroma and Ollama models.
    """

    def __init__(self, embedding_model_name: str, inference_model_name: str, documents_db_path: str, url_db_path: str, collection_name: str) -> None:
        """
        Initializes the RAG Database Manager with the specified models and database path.

        Args:
            embedding_model_name (str): The name of the Ollama embedding model to use.
            inference_model_name (str): The name of the Ollama inference model to use.
            documents_db_path (str): The directory path where the Chroma database will be stored.
            url_db_path (str): The directory path where the URLs Chroma database will be stored.
            collection_name (str): The name of the collection within the Chroma database.
        """
        self.embedding_model_name = embedding_model_name
        self.inference_model_name = inference_model_name
        self.documents_db_path = documents_db_path
        self.url_db_path = url_db_path
        self.collection_name = collection_name
        self.embedding_function = OllamaEmbeddings(
            model=self.embedding_model_name)
        self.documents_vectorstore = self._load_or_initialize_db(path=self.documents_db_path,
                                                                 collection_name=self.collection_name)
        self.urls_vectorstore = self._load_or_initialize_db(path=self.url_db_path,
                                                            collection_name=self.collection_name)
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
        self.accessed_database_in_history = []
        # Chunk parameters
        self.model_tokenizer = tiktoken.get_encoding("cl100k_base")
        self.max_token_count_per_model = {
            "gemma3:4b": 128000, "gemma3:27b": 128000}
        self.max_token_count = self.max_token_count_per_model.get(
            self.inference_model_name, 128000)
        self.chunk_size = 10000  # tokens
        self.chunk_overlap = 200  # tokens
        self.n_chunks = 5
        # Minimum similarity score to consider a match
        self.similarity_score_threshold = 0.1
        # Web based search variables
        self.urls_to_search = []

    def set_chunking_parameters(self, chunk_size: int, chunk_overlap: int) -> None:
        """
        Sets the chunking parameters for document processing.

        Args:
            chunk_size (int): The maximum number of characters in each chunk.
            chunk_overlap (int): The number of characters to overlap between chunks.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def set_chunks_to_retrieve(self, n_chunks: int) -> None:
        """
        Sets the number of chunks to retrieve during RAG prompt building.

        Args:
            n_chunks (int): The number of context chunks to retrieve.
        """
        self.n_chunks = n_chunks

    def set_similarity_score_threshold(self, threshold: float) -> None:
        """
        Sets the similarity score threshold for document retrieval.

        Args:
            threshold (float): The minimum similarity score to consider a match.
        """
        self.similarity_score_threshold = threshold

    def get_chunk_size(self) -> int:
        """
        Returns the current chunk size.

        Returns:
            int: The current chunk size.
        """
        return self.chunk_size

    def close_assistant(self) -> None:
        """
        Closes the assistant and performs any necessary cleanup, especially in the models.
        """
        subprocess.run(["ollama", "stop", self.inference_model_name])
        subprocess.run(["ollama", "stop", self.embedding_model_name])

# endregion
# region Private internal methods

    def _load_or_initialize_db(self, path: str, collection_name: str) -> Chroma:
        """
        Loads an existing DB or initializes an empty one if the path is empty/new.

        Args:
            path (str): The directory path where the Chroma database is stored.
            collection_name (str): The name of the collection within the Chroma database.

        Returns:
            Chroma: The loaded or newly created Chroma vector store.
        """
        try:
            # Try to load existing database
            db = Chroma(
                persist_directory=path,
                embedding_function=self.embedding_function,
                collection_name=collection_name,
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
                f"Creating new Chroma database structure at {path}.")
            return Chroma(
                persist_directory=path,
                embedding_function=self.embedding_function,
                collection_name=collection_name,
            )

# endregion
# region webbased methods

    def add_urls_to_search(self, urls: List[str]) -> None:
        """
        Adds the list of URLs to search during web-based retrieval.

        Args:
            urls (List[str]): A list of URLs to include in the search.
        """
        self.urls_to_search.extend(urls)

    def get_urls_to_search(self) -> List[str]:
        """
        Returns the current list of URLs to search.

        Returns:
            List[str]: The current list of URLs to search.
        """
        return self.urls_to_search

    def reset_urls_to_search(self) -> None:
        """Clears the list of URLs to search."""
        self.urls_to_search = []

    def create_database_from_urls(self) -> None:
        """
        Creates a RAG database from the content of the URLs in the urls_to_search list.
        """
        for url in self.urls_to_search:
            print(f"\n--- Adding URL Content: {url} ---")
            # Check if the document was already added to the database
            if self.urls_vectorstore:
                existing_docs = self.urls_vectorstore.similarity_search(
                    query=url, k=10)
                for doc in existing_docs:
                    if doc.metadata.get("source") == url:
                        print(
                            f"Content from '{url}' already exists in the database. Skipping addition.")
                        return

            # Loading from web and adding the chunks to the DB
            try:
                loader = WebBaseLoader(url)
                documents = loader.load()
                for doc in documents:
                    doc.page_content = doc.page_content.replace(
                        "\n", " ").strip()
                if not documents:
                    print(f"No content found at URL: {url}")
                    continue
                # Initialize Text Splitter
                text_splitter = RecursiveCharacterTextSplitter(
                    separators=["\n\n", "\n", " ", ""],
                    chunk_size=self.chunk_size,
                    chunk_overlap=self.chunk_overlap,
                )
                # Convert text chunks to LangChain Document objects and add metadata
                document_chunks = text_splitter.split_documents(documents)

                # Enhance Metadata for easier tracking
                for i, chunk in enumerate(document_chunks):
                    chunk.metadata.update({
                        "source": url,
                        "chunk_index": i,
                        "full_source": f"URL: {url}, Chunk: {i}"
                    })

                # Add documents to the Vector Store and Persist
                if document_chunks:
                    print(
                        f"Generated {len(document_chunks)} chunks of size up to {self.chunk_size}.")
                    self.urls_vectorstore.add_documents(
                        documents=document_chunks)
                    print(
                        f"Successfully added {len(document_chunks)} chunks from URL to the database.")
                else:
                    print(f"No content found at URL: {url}")
            except Exception as e:
                print(f"Error loading URL {url}: {e}")

# endregion
# region Database RAG methods

    def add_document_to_db(self, document_path: str, source_name: str) -> None:
        """
        Takes a raw document string, chunks it, and adds the chunks to the vector database.

        Args:
            document_path (str): The file path to the document to be added.
            source_name (str): A name/identifier for the document to use in the metadata.
        """
        print(f"\n--- Adding Document: {source_name} ---")
        # Check if the document was already added to the database
        if self.documents_vectorstore:
            existing_docs = self.documents_vectorstore.similarity_search(
                query=source_name, k=10)
            for doc in existing_docs:
                if doc.metadata.get("source") == source_name:
                    print(
                        f"Document '{source_name}' already exists in the database. Skipping addition.")
                    return
        # Load the document using PyPDFLoader
        loader = PyPDFLoader(document_path)
        pages = loader.load()  # Pages are returned as a list of Document objects
        # Initialize Text Splitter
        text_splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", " ", ""],
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
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
                f"Generated {len(document_chunks)} chunks of size up to {self.chunk_size}.")
            # Use Chroma's add_documents method to insert and embed the chunks
            self.documents_vectorstore.add_documents(documents=document_chunks)
            print(
                f"Successfully added {len(document_chunks)} chunks to the database.")
        else:
            print("Document was empty or too short to chunk.")

    def build_rag_prompt(self, query: str, vectorstore_name: str) -> Dict[str, Any]:
        """
        Retrieves documents from the vectorstore and builds the final RAG prompt.

        Args:
            query (str): The user's input query.
            vectorstore_name (str): The name of the vectorstore to use ('documents' or 'urls').

        Returns:
            Dict[str, Any]: Contains the final prompt string, retrieved docs, and context string.
        """
        if vectorstore_name == "documents":
            vectorstore = self.documents_vectorstore
        elif vectorstore_name == "urls":
            vectorstore = self.urls_vectorstore
        else:
            raise ValueError(f"Unknown vectorstore name: {vectorstore_name}")

        if not vectorstore:
            return {"prompt": None, "context_documents": [], "context_string": ""}

        retriever = vectorstore.as_retriever(
            search_kwargs={"k": self.n_chunks})
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

        # final_prompt_string = final_prompt_value.to_string()
        # # Debug print
        # print("\n" + "=" * 50)
        # print("🌟 FINAL PROMPT BUILT 🌟")
        # print(final_prompt_string)
        # print("=" * 50 + "\n")

        return {
            "prompt": final_prompt_value,
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
        if not self.documents_vectorstore:
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
        retriever = self.documents_vectorstore.as_retriever(
            search_kwargs={"k": 5})
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

    def format_general_user_prompt(self, user_input: str) -> ChatPromptValue:
        """
        Formats a general user input into the RAG prompt structure without retrieval.

        Args:
            user_input (str): The user's input query.

        Returns:
            ChatPromptValue: The formatted prompt.
        """
        # Fill the prompt with a default context message
        final_prompt_value = self.rag_prompt.format_prompt(
            context="Nenhum CONTEXTO fornecido. Utilize seu conhecimento ou o CONTEXTO fornecido nas mensagens de 'system' anteriores.",
            input=user_input,
        )

        # # Debug print
        # final_prompt_string = final_prompt_value.to_string()
        # print("\n" + "=" * 50)
        # print("🌟 FORMATTED USER PROMPT 🌟")
        # print(final_prompt_string)
        # print("=" * 50 + "\n")

        return final_prompt_value

    def run_inference(self, prompt: ChatPromptValue, use_history: bool) -> str:
        """
        Runs inference on a given prompt using the LLM.
        Can take either a string or a LangChain ChatPromptValue.

        Args:
            prompt (ChatPromptValue): The prepared prompt.
            use_history (bool): Whether to include message history in the LLM call.

        Returns:
            str: The model's answer.
        """
        # Find the messages to send wether from history or just the prompt
        messages = []
        if use_history and self.message_history:
            # If using history, we need to construct a full message list
            messages = self.message_history.copy()
            messages.extend(prompt.messages)
        else:
            messages = prompt.messages
        # Invoke the LLM with the messages
        response = self.llm.invoke(messages)

        return response.content

    def run_inference_pipeline(self, user_query: str, search_db: bool, use_history: bool, search_urls: bool) -> Dict[str, Any]:
        """
        Runs the full inference pipeline: builds the prompt (with or without RAG), runs inference, and returns the answer.

        Args:
            user_query (str): The user's input query.
            search_db (bool): Whether to use RAG (search the database) or just general prompt.
            use_history (bool): Whether to include message history in the LLM call.
            search_urls (bool): Whether to include web content URLs in the LLM call.

        Returns:
            Dict[str, Any]: The final response from the inference pipeline, plus sources to it.
        """
        prompt = ChatPromptValue(messages=[])
        urls_info_used = []
        if search_urls and self.urls_to_search:
            # Fetch and include web content in the prompt
            prompt_data = self.build_rag_prompt(
                query=user_query, vectorstore_name="urls")
            if prompt_data["prompt"].messages:
                prompt.messages.extend(prompt_data["prompt"].messages)
                urls_info_used = prompt_data["context_documents"]
        # Step 1: Build the prompt
        if search_db:
            prompt_data = self.build_rag_prompt(
                query=user_query, vectorstore_name="documents")
            prompt.messages.extend(prompt_data["prompt"].messages)
            # Add the sources to the history tracking if we used the DB
            if use_history:
                self.accessed_database_in_history.extend([
                    {"source": doc.metadata.get("source", "Unknown"),
                     "page": doc.metadata.get("page", "N/A")} for doc in prompt_data["context_documents"]
                ])
        if not search_db and not search_urls:
            prompt.messages.extend(self.format_general_user_prompt(
                user_input=user_query).messages)

        # Step 2: Run inference
        response = self.run_inference(prompt, use_history=use_history)

        # Step 3: Add to history if needed
        if use_history:
            self.increment_history(
                chat_messages=prompt.messages,
                assistant_response=response
            )

        return {
            "answer": response,
            "history_sources": self.accessed_database_in_history,
            "urls_used": urls_info_used
        }

# endregion
# region Message History methods

    def increment_history(self, chat_messages: list, assistant_response: str) -> None:
        """
        Updates the message history with a new user input and assistant response.

        Args:
            chat_messages (list): List of SystemMessage and HumanMessage objects.
            assistant_response (str): The assistant's response message.
        """
        # Count the tokens in the history messages
        tokens_in_history = sum(len(self.model_tokenizer.encode(
            message.content)) for message in self.message_history)
        tokens_in_new_messages = 0
        for message in chat_messages:
            # Add token count
            tokens_in_new_messages += len(
                self.model_tokenizer.encode(message.content))
            if isinstance(message, SystemMessage):
                self.message_history.append(
                    SystemMessage(content=message.content))
            elif isinstance(message, HumanMessage):
                self.message_history.append(
                    HumanMessage(content=message.content))
        tokens_in_new_messages += len(
            self.model_tokenizer.encode(assistant_response))
        self.message_history.append(AIMessage(content=assistant_response))
        # Pop old messages if we exceed a certain token limit
        if tokens_in_history + tokens_in_new_messages > self.max_token_count - 2000:
            while self.message_history and (tokens_in_history + tokens_in_new_messages) > self.max_token_count - 2000:
                removed_message = self.message_history.pop(0)
                tokens_in_history -= len(
                    self.model_tokenizer.encode(removed_message.content))

    def clear_history(self) -> None:
        """
        Clears the message history.
        """
        self.message_history = []
        self.accessed_database_in_history = []

    def get_history(self) -> list:
        """
        Returns the current message history.

        Returns:
            list: The message history with system, user, and assistant messages types.
        """
        return self.message_history

    def get_accessed_sources(self) -> list:
        """
        Returns the list of accessed sources in the current session.

        Returns:
            list: The list of accessed sources with their page numbers.
        """
        return self.accessed_database_in_history

# endregion
# region Example usage


if __name__ == "__main__":
    ############ Object creation and setup ############
    # Model to be used
    embedding_model_name = "qwen3-embedding:latest"
    inference_model_name = "gemma3:27b"

    # Initialize the AI Assistant
    print("Initializing AI Assistant...")
    ai_assistant = AiAssistant(
        embedding_model_name=embedding_model_name,
        inference_model_name=inference_model_name,
        documents_db_path="./dbs/chroma_documents_db",
        url_db_path="./dbs/chroma_url_db",
        collection_name="dev_collection"
    )

    # Setting pdf chunking parameters
    ai_assistant.set_chunking_parameters(
        chunk_size=5000, chunk_overlap=200)
    ai_assistant.set_chunks_to_retrieve(n_chunks=3)

    ############ Database formation ############
    # Example PDF files to add to the database
    # pdf_files = [
    #     "/home/vini/Downloads/Passagem - SP - Setembro.pdf",
    #     "/home/vini/Downloads/Hotel SP Setembro 2025.pdf",
    #     "/home/vini/Downloads/box 31 servicos.pdf",
    #     "/home/vini/Downloads/contrato natal.pdf",
    #     "/home/vini/Downloads/Relatório_de_Atividades___Integração_de_Dados.pdf",
    #     "/home/vini/Downloads/APEX and SOLIX G3 Operations Manual.pdf"
    # ]
    pdf_files = [
        "/home/vini/Downloads/5g_docs/COE_ELET - 00 - CÓDIGO DE CONDUTA ELETROBRAS 2024 - COMPLIANCE.pdf",
        "/home/vini/Downloads/5g_docs/PGC-GA-0001 - 02 - TRANSPORTE DE PASSAGEIROS E UTILIZAÇÃO DE VEÍCULOS - ADM.pdf",
        "/home/vini/Downloads/5g_docs/PGC-GF-0004 - 03 - REEMBOLSO DE DESPESAS E VIAGENS - FI.pdf",
        "/home/vini/Downloads/5g_docs/PGC-GSC-0001 - 01 - PGC-GSC-0001 - Procedimento de Avaliação de Fornecedores Rev Final - CONT.pdf",
        "/home/vini/Downloads/5g_docs/PLT-0001 - 02 - PLT-0001 - 02 - POLÍTICA DE TECNOLOGIA DE INFORMAÇÃO TI.pdf",
        "/home/vini/Downloads/5g_docs/PLT-0008 - 01 - PLT-0008- POLÍTICA DO SISTEMA DE GESTÃO INTEGRADA - GMASST.pdf",
    ]
    # Example URLs to add to the web-based search
    urls = [
        "https://www.in.gov.br/en/web/dou/-/resolucao-normativa-aneel-n-1.125-de-27-de-maio-de-2025-634339148",
        # "https://www.gov.br/aneel/pt-br/assuntos/noticias/2025/aneel-publica-resolucao-sobre-tratamento-especifico-a-empreendimentos-de-geracao",
    ]
    # Example queries to test
    # querys = [
    #     # {"question": "Qual é o código da minha reserva na passagem aérea para sao paulo?",
    #     #     "search_db": True, "use_history": True, "search_urls": False},
    #     # {"question": "Na primeira pergunta queria saber o 'código da reserva', na parte de informaçao da viagem, por favor me confirme novamente. Também me forneça o Nome do passageiro, e seu documento de identificaçao.", "search_db": False, "use_history": True, "search_urls": False},
    #     {"question": "Qual o objetivo desta resolução da aneel numero 1.125, faça um resumo e apresente os principais dados",
    #         "search_db": False, "use_history": False, "search_urls": True}
    # ]
    querys = [
        {"question": "Quais são os compromissos da Santo Antônio Energia em relação à saúde, segurança e meio ambiente?",
            "search_db": True, "use_history": False, "search_urls": False},
        {"question": "Como a Santo Antônio Energia promove a participação das partes interessadas no Sistema de Gestão Integrada?",
            "search_db": True, "use_history": False, "search_urls": False},
        {"question": "Quais são os principais critérios para que a Área de TI da Santo Antônio Energia defina o nível de apoio aos sistemas?",
            "search_db": True, "use_history": False, "search_urls": False},
        {"question": "Quais práticas são proibidas segundo a Política de TI da Santo Antônio Energia?",
            "search_db": True, "use_history": False, "search_urls": False},
        {"question": "Quais critérios são utilizados para avaliar fornecedores de serviços na Santo Antônio Energia?",
            "search_db": True, "use_history": False, "search_urls": False},
        {"question": "O que acontece quando um fornecedor obtém um IDF inferior a 70?",
            "search_db": True, "use_history": False, "search_urls": False},
        {"question": "Quais são os limites de reembolso para refeições durante viagens corporativas?",
            "search_db": True, "use_history": False, "search_urls": False},
        {"question": "Quais despesas não são reembolsáveis segundo o procedimento?",
            "search_db": True, "use_history": False, "search_urls": False},
        {"question": "Quais são as responsabilidades da empresa contratada no transporte de passageiros?",
            "search_db": True, "use_history": False, "search_urls": False},
        {"question": "Como funciona o transporte de integrantes em finais de semana, feriados e período noturno?",
            "search_db": True, "use_history": False, "search_urls": False},
        {"question": "Quais são os pilares que fundamentam o Código de Conduta da Eletrobras?",
            "search_db": True, "use_history": False, "search_urls": False},
        {"question": "Quais práticas são proibidas nas relações com agentes públicos?",
            "search_db": True, "use_history": False, "search_urls": False}
    ]

    ############ Adding documents to the database ############
    for pdf_file in pdf_files:
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

    ############ Running Inference ############
    q_a = []
    for query in querys:
        print("\n\n\n" + "-" * 80)
        print(f"--- Running Inference with {inference_model_name} ---")
        response_data = ai_assistant.run_inference_pipeline(user_query=query["question"],
                                                            search_db=query["search_db"],
                                                            search_urls=query["search_urls"],
                                                            use_history=query["use_history"])

        # Print the response and sources if applicable
        print(f"QUESTION: {query['question']}")
        print(f"ANSWER: {response_data['answer']}")
        print("SOURCES:")
        for doc in response_data["history_sources"]:
            print(
                f"- Document: {doc.get('source', 'Unknown')}, (Page {doc.get('page', 'N/A')})")
        for doc in response_data["urls_used"]:
            print(
                f"- TITLE: {doc.metadata.get('title', 'Unknown')}, URL: {doc.metadata.get('source', 'Unknown')}")
        print("-" * 80)

        q_a.append({"question": query['question'],
                   "answer": response_data['answer']})
    ############ Cleanup ############
    # Close the assistant and clean up resources
    ai_assistant.close_assistant()

    # Save answers to a file or database
    with open("q_and_a_ai_assistant.md", "w") as f:
        for item in q_a:
            f.write("-" * 80 + "\n")
            f.write("-" * 80 + "\n")
            f.write("-" * 80 + "\n")
            f.write(f"QUESTION: {item['question']}\n")
            f.write(f"ANSWER: {item['answer']}\n\n")

# endregion
