import paho.mqtt.client as mqtt
from typing import Any
import streamlit as st
import os
import sys
import subprocess
import json

# Add the parent directory folder to find our modules
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_path)

os.environ["OLLAMA_ACCELERATE"] = "gpu"


def assistant_response_callback(client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
    """Callback function for when a message is received on the subscribed topic.

    Args:
        client (mqtt.Client): The MQTT client instance.
        userdata (Any): User-defined data of any type.
        msg (mqtt.MQTTMessage): The received MQTT message.
    """
    # Decode the message payload
    try:
        data = msg.payload.decode('utf-8')
    except UnicodeDecodeError:
        print("Received message is not valid UTF-8.")
        return
    # Store the assistant response in the session state
    if "assistant_response" not in st.session_state:
        st.session_state.assistant_response = ""
    st.session_state.assistant_response = data
    st.session_state.new_chatbot_message = True


def chatbot_ui():
    """Streamlit UI for the chatbot agent."""
    # Initialize the control variables in the UI
    if st.session_state.chatbot_ui_initialized == False:
        # Initialize the proper agents from the workflow
        workflow = st.session_state.workflows["chatbot"]
        necessary_agents = workflow["agents"]
        input_topics = workflow["input_topics"]
        output_topics = workflow["output_topics"]
        # Call each agent docker to start
        for agent_name, input_topic, output_topic in zip(necessary_agents, input_topics, output_topics):
            docker_run_command = st.session_state.agents[agent_name]["docker_run_command"]
            docker_run_command += f" --input_topic {input_topic} --output_topic {output_topic}"
            subprocess.Popen(docker_run_command, shell=True)
        # Subscribe to the chatbot output topic
        st.session_state.chatbot_input_topic = input_topics[0]
        st.session_state.chatbot_output_topic = output_topics[0]
        st.session_state.mqtt_client.subscribe(
            st.session_state.chatbot_output_topic, qos=1)
        # Create the chatbot callback, controlling message flow with a flag
        st.session_state.mqtt_client.on_message = assistant_response_callback
        st.session_state.new_chatbot_message = False
        st.session_state.chatbot_ui_initialized = True

    # Display the app title and description
    st.title("Assistente de IA do GRIn")

    # Initialize chat history
    if "chatbot_messages" not in st.session_state:
        st.session_state.chatbot_messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.chatbot_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # React to user input
    if prompt := st.chat_input("Digite sua mensagem."):
        with st.chat_message("user"):
            st.markdown(prompt)
        # Publish the user input to the MQTT broker
        st.session_state.mqtt_client.publish(
            st.session_state.chatbot_input_topic,
            payload=json.dumps({"user_input": prompt}),
            qos=1
        )
        # Run a spinner while waiting for the assistant response
        with st.spinner("Aguardando resposta do assistente..."):
            # Wait for the assistant response
            while not st.session_state.new_chatbot_message:
                st.session_state.mqtt_client.loop(timeout=1.0)
            st.session_state.new_chatbot_message = False
        # Get the assistant response from the MQTT broker
        if "assistant_response" not in st.session_state:
            st.session_state.assistant_response = ""
        response_placeholder = st.empty()
        response_placeholder.markdown(st.session_state.assistant_response)
        # Store the assistant response in the session state
        st.session_state.chatbot_messages.append({"role": "user", "content": prompt})
        st.session_state.chatbot_messages.append(
            {"role": "assistant", "content": st.session_state.assistant_response})
