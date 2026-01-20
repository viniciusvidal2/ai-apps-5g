from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
import chromadb
from typing import Dict, Any, List
import os
import subprocess
from time import sleep


class AiAssistant:
    # region Initialization and Setup
    def __init__(self, embedding_model_name: str, inference_model_name: str, documents_db_path: str, url_db_path: str, collection_name: str) -> None:
        """
        Initializes the AI Assistant with the specified models and database path.

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
        self.expected_llm_models = ["gemma3:4b", "gemma3:12b", "gemma3:27b"]
        self.set_assistant_model(
            inference_model_name=self.inference_model_name)
        # Dealing with history of conversation
        history_client = chromadb.Client()
        self.history_vectorstore = Chroma(
            client=history_client, embedding_function=self.embedding_function)
        HISTORY_SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
            ("system", "Você resume conversas em português de forma objetiva."),
            ("human",
             "Resumo atual:\n{summary}\n\n"
             "Novas mensagens:\n{new_lines}\n\n"
             "Atualize o resumo em português."),
        ])
        self.history_summarizer = HISTORY_SUMMARY_PROMPT | self.llm
        self.history_summary = ""
        # Initialize the prompt templates for rag
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
             "Voce e um assistente de IA que ajuda a responder perguntas com base no CONTEXTO e HISTORICO DE CONVERSA fornecidos, "
             "mas tambem pode usar seu conhecimento geral. Cada CHUNK DE CONTEXTO e um trecho de um CONTEUDO de documento que pode conter informaçoes relevantes. "
             "Voce deve sempre retornar a fonte e a pagina de cada CHUNK DE CONTEXTO que voce usou para construir sua resposta. \n"
             "Este e o SUMARIO do que foi falado no HISTORICO DE CONVERSA ate agora:\n{history_summary}\n"
             "CONTEXTO:\n{history_context}\n"
             "\n{context}"),
            ("human", "{input}"),
        ])
        # Chunk parameters
        self.chunk_size = 10000  # tokens
        self.chunk_overlap = 200  # tokens
        self.n_chunks = 5
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

    def set_assistant_model(self, inference_model_name: str) -> None:
        """
        Sets the inference model for the assistant.

        Args:
            inference_model_name (str): The name of the Ollama inference model to use.
        """
        self.inference_model_name = inference_model_name
        if inference_model_name not in self.expected_llm_models:
            self.inference_model_name = self.expected_llm_models[0]
            print(
                f"Required model not found. Using inference model: {self.inference_model_name}")
        self.llm = ChatOllama(model=self.inference_model_name)

    def switch_assistant_model(self, inference_model_name: str) -> None:
        """
        Sets the inference model for the assistant.

        Args:
            inference_model_name (str): The name of the Ollama inference model to use.
        """
        # Stop the current model before switching
        subprocess.run(["ollama", "stop", self.inference_model_name])
        sleep(5)
        self.set_assistant_model(inference_model_name=inference_model_name)

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
            return db
        except Exception:
            # Create a new, empty Chroma instance for the first run
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

        # Enhance Metadata for easier tracking
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
        vectorstore = None
        if vectorstore_name == "documents":
            vectorstore = self.documents_vectorstore
        elif vectorstore_name == "urls":
            vectorstore = self.urls_vectorstore
        else:
            raise ValueError(f"Unknown vectorstore name: {vectorstore_name}")

        history_chunks = self.history_vectorstore.similarity_search(query, k=2)
        # Check if the history chunks are already in the current context as well
        history_context = "\n".join([hc.page_content for hc in history_chunks])
        # Obtain the history summary and interesting history context
        summmary_result = self.history_summarizer.invoke({
            "summary": self.history_summary,
            "new_lines": history_context,
        })
        self.history_summary = summmary_result.content

        # Retrieve relevant documents from the vectorstore
        context_string = "Nenhum CONTEXTO relevante encontrado nos documentos."
        if vectorstore:
            document_chunks = vectorstore.similarity_search(
                query, k=self.n_chunks)
            # Format retrieved docs into context
            formatted_context_chunks = [
                self.document_prompt.format(
                    page_content=dc.page_content,
                    source=dc.metadata.get("source", "Unknown"),
                    page=dc.metadata.get("page", "N/A"),
                )
                for dc in document_chunks
            ]
            context_string = "\n".join(formatted_context_chunks)

        # Fill the RAG prompt
        final_prompt_value = self.rag_prompt.format_prompt(
            history_summary=self.history_summary,
            history_context=history_context,
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
            "context_string": context_string,
        }

# endregion
# region Inference related methods

    def run_inference_pipeline(self, user_query: str) -> str:
        """
        Runs the full inference pipeline: builds the prompt (with or without RAG), runs inference, and returns the answer.

        Args:
            user_query (str): The user's input query.

        Returns:
            str: The final response from the inference pipeline.
        """
        # Step 1: Build the prompt
        prompt_data = self.build_rag_prompt(
            query=user_query, vectorstore_name="documents")

        # Step 2: Run inference
        response = self.llm.invoke(prompt_data["prompt"].messages).content

        # Step 3: Adding to history
        self.history_vectorstore.add_texts(
            [f"USUARIO: {user_query}\nCONTEXTO: {prompt_data['context_string']}\nASSISTENTE: {response}"]
        )

        return response

# endregion
# region Example usage


if __name__ == "__main__":
    ############ Object creation and setup ############
    # Model to be used
    embedding_model_name = "qwen3-embedding:0.6b"
    inference_model_name = "gemma3:12b"

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
        chunk_size=3000, chunk_overlap=200)
    ai_assistant.set_chunks_to_retrieve(n_chunks=3)

    ############ Database formation ############
    # Example PDF files to add to the database
    pdf_files = [
        "/home/vini/Downloads/Passagem - SP - Setembro.pdf",
        "/home/vini/Downloads/Hotel SP Setembro 2025.pdf",
        "/home/vini/Downloads/box 31 servicos.pdf",
        "/home/vini/Downloads/contrato natal.pdf",
        "/home/vini/Downloads/Relatório_de_Atividades___Integração_de_Dados.pdf",
        "/home/vini/Downloads/apex_manual.pdf"
    ]
    # pdf_files = [
    #     "/home/vini/Downloads/5g_docs/COE_ELET - 00 - CÓDIGO DE CONDUTA ELETROBRAS 2024 - COMPLIANCE.pdf",
    #     "/home/vini/Downloads/5g_docs/PGC-GA-0001 - 02 - TRANSPORTE DE PASSAGEIROS E UTILIZAÇÃO DE VEÍCULOS - ADM.pdf",
    #     "/home/vini/Downloads/5g_docs/PGC-GF-0004 - 03 - REEMBOLSO DE DESPESAS E VIAGENS - FI.pdf",
    #     "/home/vini/Downloads/5g_docs/PGC-GSC-0001 - 01 - PGC-GSC-0001 - Procedimento de Avaliação de Fornecedores Rev Final - CONT.pdf",
    #     "/home/vini/Downloads/5g_docs/PLT-0001 - 02 - PLT-0001 - 02 - POLÍTICA DE TECNOLOGIA DE INFORMAÇÃO TI.pdf",
    #     "/home/vini/Downloads/5g_docs/PLT-0008 - 01 - PLT-0008- POLÍTICA DO SISTEMA DE GESTÃO INTEGRADA - GMASST.pdf",
    # ]
    # Example URLs to add to the web-based search
    urls = [
        "https://www.in.gov.br/en/web/dou/-/resolucao-normativa-aneel-n-1.125-de-27-de-maio-de-2025-634339148",
        # "https://www.gov.br/aneel/pt-br/assuntos/noticias/2025/aneel-publica-resolucao-sobre-tratamento-especifico-a-empreendimentos-de-geracao",
    ]
    # Example queries to test
    querys = [
        {"question": "Qual é o código da minha reserva na passagem aérea para sao paulo?"},
        {"question": "Na primeira pergunta queria saber o 'código da reserva', na parte de informaçao da viagem, por favor me confirme novamente. Também me forneça o Nome do passageiro, e seu documento de identificaçao."},
        {"question": "No documento do contrato de natal, qual é o valor total do contrato por mês?"},
        #     {"question": "Qual o objetivo desta resolução da aneel numero 1.125, faça um resumo e apresente os principais dados"}
    ]
    # querys = [
    #     {"question": "Quais são os compromissos da Santo Antônio Energia em relação à saúde, segurança e meio ambiente?"}
    #     {"question": "Como a Santo Antônio Energia promove a participação das partes interessadas no Sistema de Gestão Integrada?"}
    #     {"question": "Quais são os principais critérios para que a Área de TI da Santo Antônio Energia defina o nível de apoio aos sistemas?"}
    #     {"question": "Quais práticas são proibidas segundo a Política de TI da Santo Antônio Energia?"}
    #     {"question": "Quais critérios são utilizados para avaliar fornecedores de serviços na Santo Antônio Energia?"}
    #     {"question": "O que acontece quando um fornecedor obtém um IDF inferior a 70?"},
    #     {"question": "Quais são os limites de reembolso para refeições durante viagens corporativas?"},
    #     {"question": "Quais despesas não são reembolsáveis segundo o procedimento?"},
    #     {"question": "Quais são as responsabilidades da empresa contratada no transporte de passageiros?"},
    #     {"question": "Como funciona o transporte de integrantes em finais de semana, feriados e período noturno?"},
    #     {"question": "Quais são os pilares que fundamentam o Código de Conduta da Eletrobras?"},
    #     {"question": "Quais práticas são proibidas nas relações com agentes públicos?"}
    # ]

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
        response = ai_assistant.run_inference_pipeline(
            user_query=query["question"])

        # Print the response and sources if applicable
        print(f"USUARIO: {query['question']}")
        print(f"ASSISTENTE: {response}")
        q_a.append({"question": query['question'],
                   "answer": response})
    ############ Cleanup ############
    # Close the assistant and clean up resources
    ai_assistant.close_assistant()

    # Save answers to a file or database
    with open("q_and_a_ai_assistant_history_change.md", "w") as f:
        for item in q_a:
            f.write("-" * 80 + "\n")
            f.write("-" * 80 + "\n")
            f.write("-" * 80 + "\n")
            f.write(f"QUESTION: {item['question']}\n")
            f.write(f"ANSWER: {item['answer']}\n\n")

# endregion
