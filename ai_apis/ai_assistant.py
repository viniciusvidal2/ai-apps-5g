from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
import chromadb
from typing import Dict, Any, List
import os
import subprocess
from time import sleep
import requests
from ai_apis.web_content_extractor import WebContentExtractor


class AiAssistant:
    # region Initialization and Setup
    def __init__(self, embedding_model_name: str, inference_model_name: str, documents_db_path: str, collection_name: str) -> None:
        """
        Initializes the AI Assistant with the specified models and database path.

        Args:
            embedding_model_name (str): The name of the Ollama embedding model to use.
            inference_model_name (str): The name of the Ollama inference model to use.
            documents_db_path (str): The directory path where the Chroma database will be stored.
            collection_name (str): The name of the collection within the Chroma database.
        """
        self.embedding_model_name = embedding_model_name
        self.inference_model_name = inference_model_name
        self.documents_db_path = documents_db_path
        self.collection_name = collection_name
        self.embedding_function = OllamaEmbeddings(
            model=self.embedding_model_name)
        self.documents_vectorstore = self._load_or_initialize_db(path=self.documents_db_path,
                                                                 collection_name=self.collection_name)

        # This assumes you have the model pulled and Ollama is running
        self.expected_llm_models = self._get_available_ollama_models()
        self.set_assistant_model(
            inference_model_name=self.inference_model_name)
        # Dealing with history of conversation
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
             "Voce deve sempre retornar a fonte e a pagina de cada CHUNK DE CONTEXTO que voce usou para construir sua resposta.\n"
             "Este e o SUMARIO do que foi falado no HISTORICO DE CONVERSA ate agora:\n{history_summary}\n"
             "CONTEXTO:\n"
             "\n{context}"),
            ("human", "{input}"),
        ])
        # Chunk parameters
        self.chunk_size = 10000  # tokens
        self.chunk_overlap = 200  # tokens
        self.n_chunks = 3
        # URL and Web content extractor
        self.web_extractor = WebContentExtractor(device="cpu")
        print("AI Assistant initialized successfully.")

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
        if inference_model_name not in self.expected_llm_models:
            self.inference_model_name = self.expected_llm_models[0]
            print(
                f"Required model not found. Using inference model: {self.inference_model_name}")
        else:
            self.inference_model_name = inference_model_name
            print(
                f"Using inference model: {self.inference_model_name}")
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

    def _get_available_ollama_models(self, base_url: str = "http://127.0.0.1:11434", timeout: int = 5) -> List[str]:
        """
        Returns a list of available Ollama model names (e.g. gemma3:4b).

        Args:
            base_url (str): The base URL of the Ollama API.
            timeout (int): The request timeout in seconds.

        Returns:
            List[str]: A list of available model names.
        """
        try:
            r = requests.get(
                f"{base_url}/api/tags",
                timeout=timeout
            )
            r.raise_for_status()
            data = r.json()
            return [m["name"] for m in data.get("models", [])]
        except requests.RequestException as e:
            print(f"Failed to query Ollama models: {e}")
            return []

# endregion
# region webbased methods

    def find_context_from_urls(self, urls: list, query: str, top_k: int = 5) -> str:
        """
        Uses the web content extractor to find relevant context from predefined URLs.

        Args:
            urls (list): A list of URLs to extract content from.
            query (str): The user's input query.
            top_k (int): The number of top relevant sections to retrieve. Default is 5.

        Returns:
            str: The combined text of the most similar chunks from all URLs.
        """
        results = []
        for url in urls:
            content = self.web_extractor.query_content_from_url(
                url=url, query=query, top_k=top_k)
            self.document_prompt.format(
                page_content=content,
                source=url,
                page="N/A",
            )
            results.append({
                "url": url,
                "content": content
            })
        combined_text = "\n\n".join([item["content"] for item in results])
        return combined_text

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

        # Retrieve relevant documents from the vectorstore
        context_string = ""
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

        # Check if we have URLs to extract context from and add to context
        urls = self.web_extractor.extract_and_validate_urls(text=query)
        if urls:
            url_context = self.find_context_from_urls(
                urls, query, top_k=self.n_chunks)
            context_string = "\n".join([context_string, url_context])

        # Fill the RAG prompt
        final_prompt_value = self.rag_prompt.format_prompt(
            history_summary=self.history_summary if self.history_summary else "Nenhuma conversa anterior.",
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

    def run_inference_pipeline(self, user_query: str, vectorstore_name: str = "documents") -> str:
        """
        Runs the full inference pipeline: builds the prompt (with or without RAG), runs inference, and returns the answer.

        Args:
            user_query (str): The user's input query.
            vectorstore_name (str): The name of the vectorstore to use ('documents' or 'None').

        Returns:
            str: The final response from the inference pipeline.
        """
        # Step 1: Build the prompt
        print("Building RAG prompt...")
        prompt_data = self.build_rag_prompt(
            query=user_query, vectorstore_name=vectorstore_name)

        # Step 2: Run inference
        print("Running inference...")
        response = self.llm.invoke(prompt_data["prompt"].messages).content

        # Step 3: Obtain the history summary from the conversation so far
        summmary_result = self.history_summarizer.invoke({
            "summary": self.history_summary,
            "new_lines": f"USUARIO: {user_query} \n CHUNKS DE CONTEXTO DA BASE DE DADOS: {prompt_data['context_string']} \n ASSISTENTE: {response}",
        })
        self.history_summary = summmary_result.content

        print("Inference pipeline completed.")
        return response

# endregion
# region Example usage


if __name__ == "__main__":
    ############ Object creation and setup ############
    # Model to be used
    embedding_model_name = "qwen3-embedding:0.6b"
    inference_model_name = "nemotron-3-nano:30b"

    # Initialize the AI Assistant
    print("Initializing AI Assistant...")
    ai_assistant = AiAssistant(
        embedding_model_name=embedding_model_name,
        inference_model_name=inference_model_name,
        documents_db_path="./dbs/chroma_documents_db",
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
    # Example queries to test
    querys = [
        {"question": "Qual é o código da minha reserva na passagem aérea para sao paulo?"},
        {"question": "Na primeira pergunta queria saber o 'código da reserva', na parte de informaçao da viagem, por favor me confirme novamente. Também me forneça o Nome do passageiro, e seu documento de identificaçao."},
        {"question": "No documento do contrato de natal, qual é o valor total do contrato por mês?"},
        {"question": "Qual é a base da multa aplicada pelas agencias conforme a resoluçao normativa sob o link https://www2.aneel.gov.br/cedoc/ren2019846.html?"}
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

    ############ Running Inference ############
    q_a = []
    for query in querys:
        print("\n\n\n" + "-" * 80)
        print(f"--- Running Inference with {inference_model_name} ---")
        response = ai_assistant.run_inference_pipeline(
            user_query=query["question"], vectorstore_name="documents")

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
