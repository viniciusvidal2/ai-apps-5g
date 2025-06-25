# helper_chatbot.py

import streamlit as st
import os
import sys

# Add the parent directory folder to find our modules
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_path)

from ai_apis.chat_with_history import ChatBot
os.environ["OLLAMA_ACCELERATE"] = "gpu"

def chatbot_ui():
    # Display the app title and description
    st.title("Assistente de IA do GRIn")

    # Initialize the chatbot
    with st.spinner("Carregando o chatbot ..."):
        model_id = "deepseek-r1:70b"
        chatbot = ChatBot(model_id=model_id)

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # React to user input
    if prompt := st.chat_input("Digite sua mensagem."):
        with st.chat_message("user"):
            st.markdown(prompt)
        assistant_response = ""
        response_placeholder = st.empty()
        with st.chat_message("ai"):
            for chunk in chatbot.chat(user_input=prompt):
                assistant_response += chunk
                response_placeholder.markdown(assistant_response)
            chatbot.updateHistory(user_input=prompt, assistant_response=assistant_response)

        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages.append({"role": "assistant", "content": assistant_response})
