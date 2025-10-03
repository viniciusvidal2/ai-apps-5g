from langchain_ollama import OllamaEmbeddings
from langchain_ollama import ChatOllama
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.prompts.chat import ChatPromptValue
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from typing import Dict, Any
import os
import subprocess


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
        # Chunk parameters
        self.chunk_size = 10000
        self.chunk_overlap = 200
        self.n_chunks = 5
        # Minimum similarity score to consider a match
        self.similarity_score_threshold = 0.1

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

    def add_document_to_db(self, document_path: str, source_name: str) -> None:
        """
        Takes a raw document string, chunks it, and adds the chunks to the vector database.

        Args:
            document_path (str): The file path to the document to be added.
            source_name (str): A name/identifier for the document to use in the metadata.
        """
        print(f"\n--- Adding Document: {source_name} ---")
        # Check if the document was already added to the database
        if self.vectorstore:
            existing_docs = self.vectorstore.similarity_search(
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
            self.vectorstore.add_documents(documents=document_chunks)
            print(
                f"Successfully added {len(document_chunks)} chunks to the database.")
        else:
            print("Document was empty or too short to chunk.")

    def build_rag_prompt(self, query: str) -> Dict[str, Any]:
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

# endregion
# region Message History methods

    def increment_history(self, system_message: str, user_input: str, assistant_response: str) -> None:
        """
        Updates the message history with a new user input and assistant response.

        Args:
            system_message (str): The system message to add.
            user_input (str): The user's input message.
            assistant_response (str): The assistant's response message.
        """
        if system_message:
            self.message_history.append(SystemMessage(content=system_message))
        if user_input and assistant_response:
            self.message_history.append(HumanMessage(content=user_input))
            self.message_history.append(AIMessage(content=assistant_response))

    def clear_history(self) -> None:
        """
        Clears the message history.
        """
        self.message_history = []

    def get_history(self) -> list:
        """
        Returns the current message history.

        Returns:
            list: The message history with system, user, and assistant messages types.
        """
        return self.message_history

# endregion
# region Example usage


if __name__ == "__main__":
    ############ Object creation and setup ############
    # Model to be used
    embedding_model_name = "qwen3-embedding:latest"
    inference_model_name = "gpt-oss:120b"

    # Initialize the AI Assistant
    print("Initializing AI Assistant...")
    ai_assistant = AiAssistant(
        embedding_model_name=embedding_model_name,
        inference_model_name=inference_model_name,
        persist_path="./chroma_db",
        collection_name="dev_collection"
    )

    # Setting pdf chunking parameters
    ai_assistant.set_chunking_parameters(
        chunk_size=5000, chunk_overlap=200)
    ai_assistant.set_chunks_to_retrieve(n_chunks=3)

    ############ Adding documents to the database ############
    # List of PDFs to add to the database
    pdf_files = [
        "/home/vini/Downloads/Passagem - SP - Setembro.pdf",
        "/home/vini/Downloads/Hotel SP Setembro 2025.pdf",
        "/home/vini/Downloads/box 31 servicos.pdf",
        "/home/vini/Downloads/contrato natal.pdf",
        "/home/vini/Downloads/Relatório_de_Atividades___Integração_de_Dados.pdf",
        "/home/vini/Downloads/APEX and SOLIX G3 Operations Manual.pdf"
    ]
    querys = [
        {"question": "Qual é o código da minha reserva na passagem aérea para sao paulo?",
            "search_db": True, "use_history": True},
        {"question": "Na primeira pergunta queria saber o 'código da reserva', na parte de informaçao da viagem, por favor me confirme novamente. Também me forneça o Nome do passageiro, e seu documento de identificaçao.", "search_db": False, "use_history": True},
        # {"question": "Qual o nome do hotel onde ficarei hospedado?", "search_db": True},
        # {"question": "Qual o valor total gasto com a passagem aerea do rio de janeiro para sao paulo?", "search_db": True},
        # {"question": "Qual meu endereço completo em Parnamirim no contrato de aluguel?",
        #     "search_db": True},
        # {"question": "Há a possibilidade de obter dados em tempo real do APEX 16 utilizando alguma porta NMEA?", "search_db": True},
    ]
    # pdf_files = [
    #     "/home/vini/Downloads/5g_docs/COE_ELET - 00 - CÓDIGO DE CONDUTA ELETROBRAS 2024 - COMPLIANCE.pdf",
    #     "/home/vini/Downloads/5g_docs/PGC-GA-0001 - 02 - TRANSPORTE DE PASSAGEIROS E UTILIZAÇÃO DE VEÍCULOS - ADM.pdf",
    #     "/home/vini/Downloads/5g_docs/PGC-GF-0004 - 03 - REEMBOLSO DE DESPESAS E VIAGENS - FI.pdf",
    #     "/home/vini/Downloads/5g_docs/PGC-GSC-0001 - 01 - PGC-GSC-0001 - Procedimento de Avaliação de Fornecedores Rev Final - CONT.pdf",
    #     "/home/vini/Downloads/5g_docs/PLT-0001 - 02 - PLT-0001 - 02 - POLÍTICA DE TECNOLOGIA DE INFORMAÇÃO TI.pdf",
    #     "/home/vini/Downloads/5g_docs/PLT-0008 - 01 - PLT-0008- POLÍTICA DO SISTEMA DE GESTÃO INTEGRADA - GMASST.pdf",
    # ]
    # querys = [
    #     "Quais são os compromissos da Santo Antônio Energia em relação à saúde, segurança e meio ambiente?",
    #     "Como a Santo Antônio Energia promove a participação das partes interessadas no Sistema de Gestão Integrada?",
    #     "Quais são os principais critérios para que a Área de TI da Santo Antônio Energia defina o nível de apoio aos sistemas?",
    #     "Quais práticas são proibidas segundo a Política de TI da Santo Antônio Energia?",
    #     "Quais critérios são utilizados para avaliar fornecedores de serviços na Santo Antônio Energia?",
    #     "O que acontece quando um fornecedor obtém um IDF inferior a 70?",
    #     "Quais são os limites de reembolso para refeições durante viagens corporativas?",
    #     "Quais despesas não são reembolsáveis segundo o procedimento?",
    #     "Quais são as responsabilidades da empresa contratada no transporte de passageiros?",
    #     "Como funciona o transporte de integrantes em finais de semana, feriados e período noturno?",
    #     "Quais são os pilares que fundamentam o Código de Conduta da Eletrobras?",
    #     "Quais práticas são proibidas nas relações com agentes públicos?",
    # ]

    # Add each PDF to the database
    for pdf_file in pdf_files:
        # Add the PDF content to the RAG database
        ai_assistant.add_document_to_db(
            document_path=pdf_file,
            source_name=os.path.basename(pdf_file)
        )

    ############ Running Inference ############
    for query in querys:
        print("\n\n\n" + "-" * 80)
        print(f"--- Running Inference with {inference_model_name} ---")
        # Look if we intend to search a database or just use the general prompt
        if query["search_db"]:
            prompt_data = ai_assistant.build_rag_prompt(
                query=query["question"])
            prompt = prompt_data["prompt"]
        else:
            prompt = ai_assistant.format_general_user_prompt(
                user_input=query["question"])

        # Run inference
        response = ai_assistant.run_inference(
            prompt=prompt, use_history=query["use_history"])

        # Update message history
        if query["use_history"]:
            ai_assistant.increment_history(
                system_message=prompt.messages[0].content,
                user_input=prompt.messages[1].content,
                assistant_response=response
            )

        # Print the response and sources if applicable
        print(f"QUERY: {query['question']}")
        print(f"ANSWER: {response}")
        if query["search_db"]:
            print("SOURCES:")
            for doc in prompt_data["context_documents"]:
                print(
                    f"- {doc.metadata.get('source', 'Unknown')}, (Page {doc.metadata.get('page', 'N/A')})")
        print("-" * 80)

    # Close the assistant and clean up resources
    ai_assistant.close_assistant()
# endregion
