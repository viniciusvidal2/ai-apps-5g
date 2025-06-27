import paho.mqtt.client as mqtt
import streamlit as st
import os
import sys
import argparse
import yaml
import subprocess
from helper_chatbot import chatbot_ui

# Add the parent directory folder to find our modules
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_path)


def kill_all_processes() -> None:
    """Kills all the agents that can be running from old processes."""
    with st.spinner("Parando outros agentes..."):
        for agent in st.session_state.agents.values():
            try:
                subprocess.run(agent["docker_stop_command"],
                            shell=True, check=False)
            except subprocess.CalledProcessError as e:
                st.error(f"Error stopping agent {agent['name']}: {e}")


def main() -> None:
    """Main function to run the UI agent."""
    # Parsing arguments for the MQTT broker address and port
    parser = argparse.ArgumentParser(description="MQTT UI agent")
    parser.add_argument(
        "--broker", "-b",
        type=str,
        required=True,
        help="MQTT broker address (e.g., 192.168.1.10)"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=1883,
        help="MQTT broker port (default: 1883)"
    )
    args = parser.parse_args()

    # General control variables in the UI
    if not "ui_initialized" in st.session_state:
        # Connect the client to the MQTT broker
        st.session_state.mqtt_client = mqtt.Client()
        st.session_state.mqtt_client.connect(args.broker, args.port)
        # Set the user ID for this session
        st.session_state.user_id = 1
        # Load the agents
        with open("agents/config/agents_config.yaml", "r") as f:
            config = yaml.safe_load(f)
            st.session_state.agents = config["agents"]
        # Add the docker control commands
        for agent in st.session_state.agents.values():
            agent["docker_run_command"] = f"docker run --rm -d --network host --name {agent['name']} {agent['name']} --broker {args.broker} --port {args.port} --user_id {st.session_state.user_id}"
            agent["docker_stop_command"] = f"docker stop {agent['name']}"
            agent["docker_remove_command"] = f"docker rm {agent['name']}"
        # Load the workflows
        with open("agents/config/workflows.yaml", "r") as f:
            config = yaml.safe_load(f)
            st.session_state.workflows = config["workflows"]
        # Tab control state variables
        st.session_state.active_page = None
        st.session_state.chatbot_ui_initialized = False
        # Set the window as initialized
        st.session_state.ui_initialized = True

    # Page config
    st.set_page_config(page_title="Assistente Inteligente SAE", layout="wide")
    st.title("Assistente Inteligente SAE")

    # Define the page titles and matching functions
    agent_pages = [
        "Chatbot",
        "Redes Neurais por planilha",
        "Análise de PDFs"
    ]

    # Layout: 2 columns (left for radio, right for button)
    col1, col2 = st.columns([3, 1])

    with col1:
        st.session_state.selected_page = st.radio(
            "Escolha o agente:", agent_pages, key="page_selector")

    with col2:
        if st.button("🚀 Lançar agente!"):
            kill_all_processes()
            st.session_state.active_page = st.session_state.selected_page

    # Now render the active agent's interface
    if st.session_state.active_page == "Chatbot":
        chatbot_ui()  # This stays rendered and interactive
    elif st.session_state.active_page == "Redes Neurais por planilha":
        st.header("Redes Neurais por planilha")
        # Call other UI or logic
    elif st.session_state.active_page == "Análise de PDFs":
        st.header("Análise de PDFs")
        # Call other UI or logic
    else:
        st.info("Selecione uma página e clique em '🚀 Lançar agente!'")


if __name__ == "__main__":
    main()
