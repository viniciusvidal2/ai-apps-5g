import streamlit as st
import sys
import os
from PIL import Image
import io

# Add the parent directory folder to find our modules
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_path)
from ai_apis.chat_with_history import ChatBot
from ai_apis.image_processor import ImageProcessor
os.environ["OLLAMA_ACCELERATE"] = "gpu"

# Initialize state variable to control the sidebar
if "sidebar_open" not in st.session_state:
    st.session_state["sidebar_open"] = False

# Initialize state to control the image popup
if "show_image_popup" not in st.session_state:
    st.session_state.show_image_popup = True

# Page configuration - always start with visible sidebar
st.set_page_config(
    page_title="AI Assistant with Image Analysis",
    layout="centered",
    initial_sidebar_state="expanded"  # Always start with sidebar visible
)

# App title
st.title("Assistente de IA com Análise de Imagens")

# Initialize chatbot and image processor
with st.spinner("Carregando os modelos..."):
    model_id = "phi4"
    chatbot = ChatBot(model_id=model_id)
    image_processor = ImageProcessor()

st.subheader("Converse com o assistente e envie imagens para análise")

# Initialize chat history and state variables
if "messages" not in st.session_state:
    st.session_state.messages = []

if "temp_image" not in st.session_state:
    st.session_state.temp_image = None

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "image" in message and message["image"] is not None:
            st.image(message["image"], width=300)

# Add image upload in sidebar
with st.sidebar:
    st.title("Opções")

    # Image uploader
    uploaded_file = st.file_uploader("Anexar imagem:", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.session_state.temp_image = image
        st.image(image, caption="Imagem anexada", width=200)

        # Display image attached indicator in sidebar
        if st.session_state.show_image_popup:
            success_col1, success_col2 = st.columns([0.9, 0.1])
            with success_col1:
                st.success("Imagem pronta para envio!")
            with success_col2:
                if st.button("✕", key="close_success"):
                    st.session_state.show_image_popup = False
                    st.rerun()

    # Button to remove image
    if st.session_state.temp_image is not None:
        if st.button("Remover imagem", use_container_width=True):
            st.session_state.temp_image = None
            st.rerun()

    # Button to clear history
    if st.button("Limpar Histórico", use_container_width=True):
        st.session_state.messages = []
        st.session_state.temp_image = None
        chatbot.clearHistory()
        st.rerun()

# React to user input
prompt = st.chat_input("Digite sua mensagem...")

if prompt:
    # Show user message
    with st.chat_message("user"):
        st.markdown(prompt)
        if st.session_state.temp_image is not None:
            st.image(st.session_state.temp_image, width=300)

    # Prepare data for processing
    user_content = prompt
    attached_image = st.session_state.temp_image

    # Add to message list
    user_message = {"role": "user", "content": user_content}
    if attached_image is not None:
        user_message["image"] = attached_image
    st.session_state.messages.append(user_message)

    # Process image if one was sent
    if attached_image is not None:
        # Get image description
        with st.spinner("Analisando imagem..."):
            image_description = image_processor.get_image_description(attached_image)
            print(image_description)
        # Prepare prompt for the chatbot - MODIFIED to avoid mentioning "provided description"
        ai_prompt = f"""O usuário enviou uma imagem e perguntou: '{user_content}'.

Descrição técnica da imagem: {image_description}

IMPORTANTE:
1. NÃO mencione que você está usando uma "descrição fornecida" ou "descrição técnica"
2. Responda como se estivesse vendo a imagem diretamente
3. Use frases como "na imagem que você enviou", "posso ver na imagem", etc.
4. Responda à pergunta do usuário com base no conteúdo visual da imagem

Sua resposta deve ser natural, como se você estivesse olhando para a imagem."""
    else:
        # No image, just text
        ai_prompt = user_content

    # Generate and show assistant response
    assistant_response = ""
    with st.chat_message("assistant"):
        response_placeholder = st.empty()

        # Process response with streaming
        with st.spinner("Gerando resposta..."):
            for chunk in chatbot.chat(user_input=ai_prompt):
                assistant_response += chunk
                response_placeholder.markdown(assistant_response)

            # Update chatbot history
            chatbot.updateHistory(user_input=ai_prompt, assistant_response=assistant_response)

    # Add assistant message to history
    st.session_state.messages.append({
        "role": "assistant",
        "content": assistant_response
    })

    # Clear temporary image after sending
    st.session_state.temp_image = None
    # Reset image popup state
    st.session_state.show_image_popup = True

    st.rerun()
