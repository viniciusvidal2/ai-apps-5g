from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from httpx import ConnectError, ConnectTimeout
import chromadb
from chromadb.utils import embedding_functions
from chromadb.config import Settings
from typing import Dict, Any, List
import subprocess
from time import sleep
import requests
from modules.web_content_extractor import WebContentExtractor


class AiAssistant:
    # region Initialization and Setup
    def __init__(self, inference_model_name: str, db_ip_address: str = "localhost") -> None:
        """
        Initializes the AI Assistant with the specified models and database path.

        Args:
            inference_model_name (str): The name of the Ollama inference model to use.
            db_ip_address (str): The IP address of the ChromaDB server. Defaults to "localhost".
        """
        self.inference_model_name = inference_model_name
        self.db_ip_address = db_ip_address
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="Qwen/Qwen3-Embedding-0.6B",
            device="cpu"
        )
        self.status = "Iniciando o assistente de IA..."

        # Connect to the ChromaDB server
        print("Connecting to ChromaDB server...")
        self.db_client = self._connect_to_chromadb()

        # This assumes you have the model pulled and Ollama is running
        self.expected_llm_models = self._get_available_ollama_models()
        self.set_assistant_model(
            inference_model_name=self.inference_model_name)
        # Dealing with history of conversation
        HISTORY_SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
            (
                "system",
                "Produza um resumo claro, objetivo e fiel em português."
            ),
            (
                "human",
                "Resumo existente:\n{summary}\n\n"
                "Novas mensagens:\n{new_lines}\n\n"
                "Atualize o resumo seguindo rigorosamente as regras abaixo:\n"
                "- Preserve integralmente o significado e os detalhes das partes que foram mais relevantes para responder à pergunta mais recente.\n"
                "- Priorize entender a intenção atual expressa nas mensagens mais recentes.\n"
                "- Informações antigas podem ser reduzidas ou removidas se não contribuírem diretamente para essa intenção.\n"
                "- Não repita instruções, papéis ou metarreferências.\n"
                "- Escreva de forma contínua, objetiva e sem listas.\n"
                "- O resultado deve servir como memória consolidada para interações futuras."
            ),
        ])
        self.history_summarizer = HISTORY_SUMMARY_PROMPT | self.llm
        self.history_summary = ""
        # Query improvement stage
        QUERY_IMPROVEMENT_PROMPT = ChatPromptTemplate.from_messages([
            (
                "system",
                """Voce e um assistente de IA especializado em reformular perguntas para maximizar a relevância dos resultados recuperados de uma base de dados e da web. 
                Sua tarefa é pegar a pergunta original do usuário e reescrevê-la de forma mais clara, 
                objetiva e detalhada, mantendo o significado original, 
                mas melhorando a formulação para obter melhores respostas do assistente de IA.
                """,
            ),
            (
                "human",
                """Dada a pergunta do usuário abaixo, reescreva-a para ser mais clara, objetiva e detalhada, 
                de forma a maximizar a relevância dos resultados recuperados da base de dados e da web. 
                Mantenha o significado original, mas melhore a formulação para obter melhores respostas do assistente de IA.\n
                "Pergunta original: {input}""",
            ),
        ])
        self.query_improver = QUERY_IMPROVEMENT_PROMPT | self.llm
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
             "Voce e um assistente de IA que ajuda a responder perguntas com base no CONTEXTO e SUMARIO do HISTORICO DE CONVERSA fornecidos, "
             "mas tambem pode usar seu conhecimento geral. Cada CHUNK DE CONTEXTO e um trecho de um CONTEUDO de documento que pode conter informaçoes relevantes. "
             "Voce deve sempre retornar a fonte e a pagina de cada CHUNK DE CONTEXTO que voce usou para construir sua resposta.\n"
             "Este e o SUMARIO do que foi falado no HISTORICO DE CONVERSA ate agora:\n{history_summary}\n"
             "CONTEXTO:\n{context}\n"),
            ("human", "PERGUNTA ATUAL: {input}"),
        ])
        # Chunk parameters
        self.n_chunks = 3
        # URL and Web content extractor
        self.web_extractor = WebContentExtractor(device="cpu")
        # Assistant status string for agent analysis
        self.status = "Assistente inicializado e pronto para processar mensagens."
        print("AI Assistant initialized successfully.")

    def _connect_to_chromadb(self) -> chromadb.api.client.Client:
        """
        Connects to the ChromaDB server and returns the client instance.

        Returns:
            chromadb.api.Client: The connected ChromaDB client instance.
        """
        try:
            client = chromadb.HttpClient(
                host=self.db_ip_address,
                port=8000,
                settings=Settings(
                    chroma_server_ssl_verify=False
                )
            )
            client.heartbeat()
            print(
                f"✅ Successfully connected to ChromaDB at {self.db_ip_address}:8000")
            return client
        except (ConnectError, ConnectTimeout) as e:
            print(
                f"❌ Connection Failed: Could not reach ChromaDB at {self.db_ip_address}:8000.")
            print(f"Internal Error: {e}")
            return None
        except Exception as e:
            print(
                f"⚠️ An unexpected error occurred during initialization: {e}")
            return None

    def set_chunks_to_retrieve(self, n_chunks: int) -> None:
        """
        Sets the number of chunks to retrieve during RAG prompt building.

        Args:
            n_chunks (int): The number of context chunks to retrieve.
        """
        self.n_chunks = n_chunks

    def set_assistant_conversation_summary(self, summary: str) -> None:
        """
        Manually sets the conversation summary for the assistant.

        Args:
            summary (str): The conversation summary string to set.
        """
        self.history_summary = summary

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
        """Closes the assistant and performs any necessary cleanup, especially in the models."""
        subprocess.run(["ollama", "stop", self.inference_model_name])
        print("Assistant closed and resources cleaned up.")

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

    def get_assistant_status(self) -> str:
        """
        Returns the current status of the assistant for agent analysis.

        Returns:
            str: The current status string of the assistant.
        """
        return self.status

    def get_assistant_conversation_summary(self) -> str:
        """
        Returns the current conversation summary of the assistant.

        Returns:
            str: The current conversation summary.
        """
        return self.history_summary

    def get_collection_names(self) -> List[str]:
        """
        Returns the list of collection names available in the database.

        Returns:
            List[str]: The list of collection names available in the database.
        """
        if self.db_client is not None:
            try:
                collections = self.db_client.list_collections()
                return [col.name for col in collections]
            except Exception as e:
                print(f"Error retrieving collections from the database: {e}")
                return []
        else:
            print("Database client is not initialized.")
            return []

    def get_inference_model_name(self) -> str:
        """
        Returns the name of the current inference model being used by the assistant.

        Returns:
            str: The name of the current inference model.
        """
        return self.inference_model_name

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
# region Inference related methods

    def build_rag_prompt(self, query: str, collection_name: str) -> Dict[str, Any]:
        """
        Retrieves documents from the vectorstore and builds the final RAG prompt.

        Args:
            query (str): The user's input query.
            collection_name (str): The name of the collection to use ('documents' or 'none').

        Returns:
            Dict[str, Any]: Contains the final prompt string, retrieved docs, and context string.
        """
        # Improve query formulation before retrieval to maximize relevance of retrieved chunks
        print("Improving query formulation for better retrieval...")
        self.status = "Melhorando a formulação da consulta."
        improved_query = self.query_improver.invoke({"input": query}).content

        # Retrieve relevant documents from the vectorstore
        print("Retrieving relevant documents from the vectorstore...")
        self.status = "Recuperando documentos relevantes da base de dados."
        context_string = ""
        if self.db_client is not None:
            try:
                collection = self.db_client.get_collection(
                    name=collection_name, embedding_function=self.ef)
                results = collection.query(
                    query_texts=[improved_query],
                    n_results=self.n_chunks,
                )
                formatted_context_chunks = [
                    self.document_prompt.format(
                        page_content=dc,
                        source=md.get("document_name", "Unknown"),
                        page=md.get("page_number", "N/A"),
                    )
                    for dc, md in zip(results['documents'][0], results['metadatas'][0])
                ]
                context_string = "\n".join(formatted_context_chunks)
            except Exception as e:
                print(f"Error retrieving documents from the database: {e}")
                self.status = "Base de dados inacessível. Não foi possível recuperar documentos."

        # Check if we have URLs to extract context from and add to context
        urls = self.web_extractor.extract_and_validate_urls(text=query)
        if urls:
            print(
                f"Found URLs in the query. Extracting relevant context from the web for {len(urls)} URLs...")
            self.status = "Extraindo contexto relevante das URLs fornecidas."
            url_context = self.find_context_from_urls(
                urls, query, top_k=self.n_chunks)
            context_string = "\n".join([context_string, url_context])

        # Fill the RAG prompt
        print("Filling the RAG prompt with retrieved context and conversation history...")
        self.status = "Preenchendo o prompt RAG final."
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

    def run_inference_pipeline(self, user_query: str, collection_name: str = "documents") -> str:
        """
        Runs the full inference pipeline: builds the prompt (with or without RAG), runs inference, and returns the answer.

        Args:
            user_query (str): The user's input query.
            collection_name (str): The name of the collection to use ('documents' or 'None').

        Returns:
            str: The final response from the inference pipeline.
        """
        # Step 1: Build the prompt
        print("Building RAG prompt...")
        self.status = "Construindo o prompt para a consulta do usuário."
        prompt_data = self.build_rag_prompt(
            query=user_query, collection_name=collection_name)
        # Step 2: Run inference
        print("Running inference...")
        self.status = "Executando inferência com a IA."
        response = self.llm.invoke(prompt_data["prompt"].messages).content

        # Step 3: Obtain the history summary from the conversation so far
        self.status = "Atualizando o resumo do histórico da conversa."
        summmary_result = self.history_summarizer.invoke({
            "summary": self.history_summary,
            "new_lines": f"USUARIO: {user_query} \n CHUNKS DE CONTEXTO DA BASE DE DADOS: {prompt_data['context_string']} \n ASSISTENTE: {response}",
        })
        self.history_summary = summmary_result.content

        self.status = "Inferência concluída com sucesso. Assistente está pronto para processar mensagens."
        print("Inference pipeline completed.")
        return response

# endregion
# region Example usage


if __name__ == "__main__":
    ############ Object creation and setup ############
    # Model to be used
    inference_model_name = "nemotron-3-nano:30b"

    # Initialize the AI Assistant
    print("Initializing AI Assistant...")
    ai_assistant = AiAssistant(
        inference_model_name=inference_model_name,
        db_ip_address="localhost"
    )
    ai_assistant.set_chunks_to_retrieve(n_chunks=3)

    # Example queries to test
    # querys = [
    #     {"question": "Qual é o código da minha reserva na passagem aérea para sao paulo?"},
    #     {"question": "Na primeira pergunta queria saber o 'código da reserva', na parte de informaçao da viagem, por favor me confirme novamente. Também me forneça o Nome do passageiro, e seu documento de identificaçao."},
    #     {"question": "No documento do contrato de natal, qual é o valor total do contrato por mês?"},
    #     {"question": "Qual é a base da multa aplicada pelas agencias conforme a resoluçao normativa sob o link https://www2.aneel.gov.br/cedoc/ren2019846.html?"}
    # ]
    querys = [
        {"question": "Quais são os compromissos da Santo Antônio Energia em relação à saúde, segurança e meio ambiente?"},
        {"question": "Como a Santo Antônio Energia promove a participação das partes interessadas no Sistema de Gestão Integrada?"},
        {"question": "Quais são os principais critérios para que a Área de TI da Santo Antônio Energia defina o nível de apoio aos sistemas?"},
        {"question": "Quais práticas são proibidas segundo a Política de TI da Santo Antônio Energia?"},
        {"question": "Quais critérios são utilizados para avaliar fornecedores de serviços na Santo Antônio Energia?"},
        {"question": "O que acontece quando um fornecedor obtém um IDF inferior a 70?"},
        {"question": "Quais são os limites de reembolso para refeições durante viagens corporativas?"},
        {"question": "Quais despesas não são reembolsáveis segundo o procedimento?"},
        {"question": "Quais são as responsabilidades da empresa contratada no transporte de passageiros?"},
        {"question": "Como funciona o transporte de integrantes em finais de semana, feriados e período noturno?"},
        {"question": "Quais são os pilares que fundamentam o Código de Conduta da Eletrobras?"},
        {"question": "Quais práticas são proibidas nas relações com agentes públicos?"}
    ]

    ############ Running Inference ############
    q_a = []
    for query in querys:
        print("\n\n\n" + "-" * 80)
        print(f"--- Running Inference with {inference_model_name} ---")
        response = ai_assistant.run_inference_pipeline(
            user_query=query["question"], collection_name="my_collection")

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
