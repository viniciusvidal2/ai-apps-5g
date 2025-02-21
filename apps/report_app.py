"""
Audio Report Generator Application
--------------------------------
A Streamlit application that converts audio input (file upload or voice recording)
into text and generates structured reports using AI models.

Main features:
- Audio file upload support
- Real-time voice recording
- Text transcription using Whisper
- Report generation using LLaMA
- Export capabilities for generated reports
"""

import streamlit as st
import tempfile
import os
import sounddevice as sd
import soundfile as sf
import numpy as np
import sys

# Add the parent directory folder to find our modules
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_path)

from ai_apis.audio_to_text import runWhisper
from ai_apis.report_generation import generateReportWithModel
from ai_apis.pull_model_ollama import pullModel

# Configure page settings
st.set_page_config(page_title="Audio Report Generator", layout="wide")

# Hide unnecessary UI elements
hide_menu_style = """
    <style>
    #MainMenu {visibility: hidden;}
    .stDeployButton {display: none;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
"""
st.markdown(hide_menu_style, unsafe_allow_html=True)

# Define model IDs
WHISPER_MODEL = "openai/whisper-large-v3-turbo"
LLM_MODEL = "llama3.2"
SAMPLE_RATE = 16000

# Initialize session state
if 'audio_recording' not in st.session_state:
    st.session_state.audio_recording = False
if 'audio_data' not in st.session_state:
    st.session_state.audio_data = []
if 'transcription' not in st.session_state:
    st.session_state.transcription = ""
if 'report' not in st.session_state:
    st.session_state.report = ""

# Main application title and description
st.title("Audio Report Generator")
st.markdown("""
    Generate reports from your voice or audio files. You can:
    - Upload an audio file
    - Record your voice directly
    - Type or edit the text before generating the report
""")

# Create two columns for input methods
col1, col2 = st.columns(2)

with col1:
    st.subheader("📁 Audio File Upload")
    audio_file = st.file_uploader("Drop your audio file here", type=["mp3", "mpeg", "wav", "ogg"],
                                 label_visibility="collapsed")

with col2:
    st.subheader("🎤 Voice Recording")
    # Recording controls
    if not st.session_state.audio_recording:
        if st.button("Start Recording", use_container_width=True):
            st.session_state.audio_recording = True
            st.session_state.audio_data = []
            st.rerun()
    else:
        if st.button("Stop Recording", use_container_width=True, type="primary"):
            st.session_state.audio_recording = False

            # Save and process recorded audio
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                audio_data = np.concatenate(st.session_state.audio_data, axis=0)
                sf.write(tmp.name, audio_data, SAMPLE_RATE)

                with st.spinner("Transcribing audio..."):
                    st.session_state.transcription = runWhisper(
                        model_id=WHISPER_MODEL,
                        audio_path=tmp.name
                    )
                os.remove(tmp.name)

            st.session_state.audio_data = []
            st.rerun()

# Show recording status
if st.session_state.audio_recording:
    st.warning("⚡ Recording in progress... Speak your text for the report")
    duration = 0.1
    audio_chunk = sd.rec(int(duration * SAMPLE_RATE),
                        samplerate=SAMPLE_RATE,
                        channels=1,
                        dtype=np.float32)
    sd.wait()
    st.session_state.audio_data.append(audio_chunk)
    st.rerun()

# Process uploaded audio file
if audio_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".tmp") as tmp:
        tmp.write(audio_file.getbuffer())
        temp_path = tmp.name

    with st.spinner("Transcribing audio..."):
        st.session_state.transcription = runWhisper(
            model_id=WHISPER_MODEL,
            audio_path=temp_path
        )
    os.remove(temp_path)

# Text editing section
st.subheader("📝 Text Editor")
text_input = st.text_area(
    "Edit transcription or type your text here",
    value=st.session_state.transcription,
    height=200,
    label_visibility="collapsed"
)

# Generate report button
if st.button("Generate Report", use_container_width=True, type="primary"):
    if text_input:
        with st.spinner("Generating report..."):
            if not pullModel(LLM_MODEL):
                st.error("Error loading LLM model")
            else:
                st.session_state.report = generateReportWithModel(
                    model_id=LLM_MODEL,
                    message=text_input
                )
    else:
        st.warning("Please provide some text before generating the report")

# Display generated report
if st.session_state.report:
    st.subheader("📊 Generated Report")
    st.markdown(st.session_state.report)
