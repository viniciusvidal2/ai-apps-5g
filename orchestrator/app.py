import streamlit as st
import os
import sys
from helper_chatbot import chatbot_ui

# Add the parent directory folder to find our modules
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_path)

st.set_page_config(page_title="Assistente Inteligente SAE", layout="wide")
st.title("Assistente Inteligente SAE")

# Create the tabs
tab_titles = ["Chatbot", "Redes Neurais por planilha", "Análise de PDFs"]
tabs = st.tabs(tab_titles)

# Populate each tab with proper helper functions
with tabs[0]:
    chatbot_ui()

with tabs[1]:
    st.header("Redes Neurais por planilha")

with tabs[2]:
    st.header("Análise de PDFs")
