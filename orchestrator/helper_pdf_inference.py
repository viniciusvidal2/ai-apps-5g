import paho.mqtt.client as mqtt
from typing import Any
import streamlit as st
import os
import sys
import json
import time
from tools import launch_agents_from_workflow

# Add the parent directory folder to find our modules
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_path)


def on_message(client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
    """Callback function for when a message is received on the subscribed topic.

    Args:
        client (mqtt.Client): The MQTT client instance.
        userdata (Any): User-defined data of any type.
        msg (mqtt.MQTTMessage): The received MQTT message.
    """
    # Decode the message payload
    payload = msg.payload.decode('utf-8')
    data = json.loads(payload)
    # Check the topic of the message and update the session state accordingly
    if msg.topic == st.session_state.pdf_inference_page_data["pdf_prompt_topic"]:
        # Get the PDF data from the message and create the proper formatted prompt
        formatted_prompt = f"""
            Instrucao: A seguir, voce recebera o conteudo de um PDF dividido em duas partes: texto e imagens.
            A primeira parte contem o texto do PDF, e a segunda parte contem as imagens do PDF.
            Sua tarefa e analisar o conteudo do PDF e responder a pergunta que sera feita a seguir
            com base no conteudo do PDF.
            Texto do PDF:
            {data["text"]}
            Imagens do PDF:
            {data["images"]}
            Pergunta: {st.session_state.pdf_inference_page_data["inference_prompt"]}
            Resposta:
        """
        # Publish this prompt to the chatbot agent
        st.session_state.mqtt_client.publish(
            st.session_state.pdf_inference_page_data["assistant_input_topic"],
            payload=json.dumps({"user_input": formatted_prompt}),
            qos=1
        )
    elif msg.topic == st.session_state.pdf_inference_page_data["assistant_response_topic"]:
        # Store the assistant response in the session state
        st.session_state.pdf_inference_page_data["assistant_response"] = (
            data["assistant_response"].replace('\n', '\n\n')
        )
        st.session_state.pdf_inference_page_data["assistant_response_arrived"] = True


def pdf_inference_ui():
    """Streamlit UI for the PDF inference agent."""
    # Initialize the control variables in the UI
    if not st.session_state.pdf_inference_page_data:
        st.session_state.pdf_inference_page_data = {}
        # Initialize the proper agents from the workflow
        workflow = st.session_state.workflows["pdf_inference"]
        # Call each agent docker to start
        launch_agents_from_workflow(
            workflow=workflow, agents=st.session_state.agents)
        # Subscribe to the PDF prompt topic and assistant response topic
        st.session_state.pdf_inference_page_data["pdf_data_topic"] = workflow["input_topics"][0]
        st.session_state.pdf_inference_page_data["pdf_prompt_topic"] = workflow["output_topics"][0]
        st.session_state.pdf_inference_page_data["assistant_input_topic"] = workflow["input_topics"][1]
        st.session_state.pdf_inference_page_data["assistant_response_topic"] = workflow["output_topics"][1]
        st.session_state.mqtt_client.subscribe(
            st.session_state.pdf_inference_page_data["pdf_prompt_topic"], qos=1)
        st.session_state.mqtt_client.subscribe(
            st.session_state.pdf_inference_page_data["assistant_response_topic"], qos=1)
        # Create the callback, controlling incoming messages or pdf info
        st.session_state.mqtt_client.on_message = on_message
        st.session_state.pdf_inference_page_data["assistant_response_arrived"] = False
        st.session_state.pdf_inference_page_data["question_pdf_ready"] = False
        # Assistant response
        st.session_state.pdf_inference_page_data["assistant_response"] = ""
        # Initialize chat history
        st.session_state.pdf_inference_page_data["messages"] = []

    # Display the app title and description
    st.title("Assistente de PDFs")

    # Layout: input and file uploader side by side
    col1, col2 = st.columns([2, 1])
    with col1:
        # Display chat messages from history on app rerun
        for message in st.session_state.pdf_inference_page_data["messages"]:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        st.session_state.pdf_inference_page_data["inference_prompt"] = st.text_area(
            "Busca sobre o PDF anexado:",
            placeholder="Escreva instruções ou perguntas relacionadas ao seu PDF...",
            key="user_text"
        )
    with col2:
        st.session_state.pdf_inference_page_data["uploaded_file"] = st.file_uploader(
            "Anexar um arquivo PDF",
            type=["pdf"],
            key="pdf_file"
        )
    # Process button
    if st.button("Process"):
        if st.session_state.pdf_inference_page_data["inference_prompt"] and st.session_state.pdf_inference_page_data["uploaded_file"]:
            st.session_state.pdf_inference_page_data["question_pdf_ready"] = True
        else:
            st.warning(
                "Por favor, forneça tanto o texto de entrada quanto um arquivo PDF.")

    if st.session_state.pdf_inference_page_data["question_pdf_ready"]:
        # Convert the PDF into binary data and send the request
        pdf_bytes = st.session_state.pdf_inference_page_data["uploaded_file"].read(
        )
        st.session_state.mqtt_client.publish(
            st.session_state.pdf_inference_page_data["pdf_data_topic"],
            payload=pdf_bytes,
            qos=1
        )
        # While message is not received, spin and wait
        with st.spinner("Processando... Por favor, aguarde."):
            while not st.session_state.pdf_inference_page_data["assistant_response_arrived"]:
                st.session_state.mqtt_client.loop(timeout=1.0)
            st.session_state.pdf_inference_page_data["assistant_response_arrived"] = False
        # Print the assistant response from the MQTT broker
        response_placeholder = st.empty()
        typed_response = ""
        for char in st.session_state.pdf_inference_page_data["assistant_response"]:
            typed_response += char
            response_placeholder.markdown(typed_response)
            # Simulate typing effect
            time.sleep(0.01)
        # Store the assistant response in the session state
        st.session_state.pdf_inference_page_data["messages"].append(
            {"role": "user", "content": st.session_state.pdf_inference_page_data["inference_prompt"]})
        st.session_state.pdf_inference_page_data["messages"].append(
            {"role": "assistant", "content": st.session_state.pdf_inference_page_data["assistant_response"]})
    else:
        st.warning(
            "Por favor, forneça tanto o texto de entrada quanto um arquivo PDF.")
