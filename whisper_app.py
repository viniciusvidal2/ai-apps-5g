"""
Whisper Transcription Web Interface

This module provides a Streamlit-based web interface for audio transcription using OpenAI's Whisper model.
It allows users to upload audio files and get Portuguese transcriptions.

Author: Your Name
Date: March 2024
"""

import streamlit as st
import tempfile
import os
from ai_apis.audio_to_text import runWhisper

# Configure Streamlit page settings and hide unnecessary UI elements
hide_menu_style = """
    <style>
    #MainMenu {visibility: hidden;}
    .stDeployButton {display: none;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_menu_style, unsafe_allow_html=True)

# Main application title
st.title("Transcrição")

# Model configuration section
# The default model is set to whisper-large-v3-turbo which provides good results for Portuguese
model_id = st.text_input(
    "Model ID",
    value="openai/whisper-large-v3-turbo",
    help="Insira o ID do modelo Whisper a ser utilizado."
)

# File upload section
# Accepts common audio formats: mp3, mpeg, wav, ogg
audio_file = st.file_uploader("Select an audio file", type=["mp3", "mpeg", "wav", "ogg"])

if audio_file is not None:
    try:
        # Create a temporary file to process the uploaded audio
        # This is needed because Whisper requires a file path
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp:
            tmp.write(audio_file.getbuffer())
            temp_path = tmp.name

        # Process the audio file and display progress indicators
        st.write("Processing audio, please wait...")
        with st.spinner("Transcribing audio..."):
            transcription = runWhisper(model_id=model_id, audio_path=temp_path)

        # Display the transcription results
        st.subheader("Transcrição")
        st.write(transcription)

    except Exception as e:
        # Handle potential errors during processing
        st.error(f"An error occurred during transcription: {str(e)}")

    finally:
        # Cleanup: Remove temporary file
        if 'temp_path' in locals():
            os.remove(temp_path)
