import paho.mqtt.client as mqtt
import streamlit as st
import os
import sys
import argparse
import yaml
from helper_chatbot import chatbot_ui

# Add the parent directory folder to find our modules
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_path)


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
        st.session_state.active_tab = None
        st.session_state.active_process = None
        # Set the window as initialized
        st.session_state.ui_initialized = True

    # Set the page configuration
    st.set_page_config(page_title="Assistente Inteligente SAE", layout="wide")
    st.title("Assistente Inteligente SAE")

    # Create the tabs
    st.session_state.tab_titles = [
        "Chatbot", "Redes Neurais por planilha", "Análise de PDFs"]
    tabs = st.tabs(st.session_state.tab_titles)
    st.session_state.active_tab = st.session_state.tab_titles[0]

    # Populate each tab with proper helper functions
    with tabs[0]:
        if st.session_state.active_tab != st.session_state.tab_titles[0]:
            st.session_state.active_tab = st.session_state.tab_titles[0]
        chatbot_ui()
    print(st.session_state.active_tab)
    with tabs[1]:
        if st.session_state.active_tab != st.session_state.tab_titles[1]:
            st.session_state.active_tab = st.session_state.tab_titles[1]
        st.header("Redes Neurais por planilha")
    print(st.session_state.active_tab)
    with tabs[2]:
        if st.session_state.active_tab != st.session_state.tab_titles[2]:
            st.session_state.active_tab = st.session_state.tab_titles[2]
        st.header("Análise de PDFs")
    print(st.session_state.active_tab)


if __name__ == "__main__":
    main()
