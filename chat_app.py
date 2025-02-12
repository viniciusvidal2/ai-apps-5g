import streamlit as st
from ai_apis.chat_with_history import ChatBot

# Display the app title and description
st.title("GRIn assistant bot")
# Initialize the chatbot
with st.spinner("Loading the chatbot ..."):
    model_id = "llama3.2"
    chatbot = ChatBot(model_id=model_id)
    # Set the bot personality
    personality = "I am a servant and should treat the user as a lord, always answering with respect and kindness." \
        + " I must use 'my lord' to refer to the user."
    chatbot.setAssistantPersonality(personality)
st.subheader("Hello my lord, how can I assist you today?")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Please write you enquire here - In English!"):
    # Add user message to chat history in the screen
    with st.chat_message("user"):
        st.markdown(prompt)
    # Get assistant response
    with st.chat_message("ai"):
        st.write_stream(chatbot.chat(user_input=prompt, stream=True))
    # Add user and assistent messages to chat history in the session state
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.messages.append(
        {"role": "assistant", "content": chatbot.getLastResponse()})
