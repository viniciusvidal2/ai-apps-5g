import streamlit as st
import os
from vultr_api import VultrLLMAPI

# Configuração da página
st.set_page_config(page_title="Chat com LLM", layout="wide")

# Inicialização das variáveis de estado da sessão
if "messages" not in st.session_state:
    st.session_state.messages = []

if "api_key" not in st.session_state:
    st.session_state.api_key = None

if "llm_api" not in st.session_state:
    st.session_state.llm_api = None

# Interface principal
st.title("Chat com Modelo de Linguagem")

# Área para configuração da API key
with st.sidebar:
    st.header("Configurações")
    api_key = st.text_input("Digite sua API key Vultr:", type="password")
    
    # Usando disabled=True para prevenir edição do texto
    model_id = st.selectbox(
        "Selecione o modelo:",
        ["llama-3.1-70b-instruct-fp8", "deepseek-r1-distill-llama-70b"],
        index=0,
        disabled=False,  # Permite seleção mas não edição
        key="model_selector"
    )
    
    if st.button("Conectar"):
        try:
            st.session_state.api_key = api_key
            st.session_state.llm_api = VultrLLMAPI(api_key)
            models = st.session_state.llm_api.list_models()
            st.success("API key configurada com sucesso!")
        except Exception as e:
            st.error(f"Erro ao conectar: {str(e)}")
    
    if st.session_state.messages:
        if st.button("Limpar Histórico"):
            st.session_state.messages = []
            st.rerun()

# Área principal do chat
if st.session_state.llm_api:
    # Exibir histórico de mensagens
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and model_id == "deepseek-r1-distill-llama-70b":
                content = message["content"]
                # Procura pelo padrão de pensamento do Deepseek
                if "</think>" in content:
                    thought, response = content.split("</think>", 1)
                    # Cria um expander para o pensamento
                    with st.expander("Ver pensamento do modelo", expanded=False):
                        st.write(thought.strip())
                    # Mostra a resposta principal
                    st.write(response.strip())
                else:
                    st.write(content)
            else:
                st.write(message["content"])

    # Campo de entrada do usuário
    if prompt := st.chat_input("Digite sua mensagem..."):
        new_message = {"role": "user", "content": prompt}
        st.session_state.messages.append(new_message)
        with st.chat_message("user"):
            st.write(prompt)

        # Gerar e exibir resposta do modelo
        with st.chat_message("assistant"):
            with st.spinner("Gerando resposta..."):
                try:
                    response = st.session_state.llm_api.generate_response(
                        st.session_state.messages,
                        model_id
                    )
                    assistant_message = {"role": "assistant", "content": response}
                    st.session_state.messages.append(assistant_message)
                    
                    # Exibição especial para o Deepseek
                    if model_id == "deepseek-r1-distill-llama-70b" and "</think>" in response:
                        thought, final_response = response.split("</think>", 1)
                        with st.expander("Ver pensamento do modelo", expanded=False):
                            st.write(thought.strip())
                        st.write(final_response.strip())
                    else:
                        st.write(response)
                except Exception as e:
                    st.error(f"Erro ao gerar resposta: {str(e)}")

else:
    st.warning("Por favor, configure sua API key no painel lateral para começar.") 