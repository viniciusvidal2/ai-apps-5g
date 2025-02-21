import os
import time
import argparse
import sys

# Add the parent directory folder to find our modules
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_path)

from ai_apis.summarize_text import runBartSummarizer
from ai_apis.audio_to_text import runWhisper


def main(audio_path: str) -> None:
    """Generates a summary from an audio file.

    Args:
        audio_path (str): input audio file path
    """
    # Measuring time
    start_time = time.time()

    # Define model ids
    summarizer_model_id = "facebook/bart-large-cnn"
    whisper_model_id = "openai/whisper-large-v3-turbo"

    # Calling the models in sequence
    text_prompt = runWhisper(model_id=whisper_model_id, audio_path=audio_path)
    summary = runBartSummarizer(
        text_prompt=text_prompt, model_id=summarizer_model_id, min_length_pct=0.1, max_length_pct=0.5)
    
    time_elapsed = time.time() - start_time

    print("This is the input text:\n")
    print(text_prompt)
    print("\n\nThis is the output summary:")
    print(summary)
    print(f"\nTime elapsed: {time_elapsed} seconds")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process an audio file and generate a summary.")
    parser.add_argument("--audio_file", type=str, help="Path to the audio file",
                        default=os.path.join(os.getenv("HOME"), "Downloads/secao_3.mpeg"))
    args = parser.parse_args()

    main(audio_path=args.audio_file)
