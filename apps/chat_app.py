import streamlit as st
import sys
import os
# Add the parent directory folder to find our modules
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_path)
from ai_apis.chat_with_history import ChatBot
os.environ["OLLAMA_ACCELERATE"] = "gpu"


# Display the app title and description
st.title("Assistente de IA da SAE")
# Initialize the chatbot
with st.spinner("Carregando o chatbot ..."):
    model_id = "sae-assistant-phi4"
    chatbot = ChatBot(model_id=model_id)
st.subheader("Converse com o assistente para auxilia-lo em suas tarefas")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Digite sua mensagem."):
    # Add user message to chat history in the screen
    with st.chat_message("user"):
        st.markdown(prompt)
    # Capture the assistant streamed response
    assistant_response = ""
    response_placeholder = st.empty()
    with st.chat_message("ai"):
        for chunk in chatbot.chat(user_input=prompt):
            assistant_response += chunk
            response_placeholder.markdown(assistant_response)
        chatbot.updateHistory(user_input=prompt, assistant_response=assistant_response)
    # Add user and assistent messages to chat history in the session state
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.messages.append({"role": "assistant", "content": assistant_response})
