import os
import time
import argparse
from ai_apis.pull_model_ollama import pullModel
from ai_apis.report_generation import generateReportWithModel
from ai_apis.audio_to_text import runWhisper


def main(audio_path: str) -> None:
    """Generates a report from an audio file.

    Args:
        audio_path (str): input audio file path
    """
    # Measuring time
    start_time = time.time()

    # Getting text from the audio
    whisper_model_id = "openai/whisper-large-v3-turbo"
    text_prompt = runWhisper(model_id=whisper_model_id, audio_path=audio_path)

    # Pull the proper ollama model
    ollama_model_id = "llama3.2"
    model_downloaded = pullModel(model_id=ollama_model_id)
    if not model_downloaded:
        print("Error downloading the model")
        return

    # Generate the report
    report = generateReportWithModel(
        model_id=ollama_model_id, message=text_prompt)

    time_elapsed = time.time() - start_time

    print("This is the input text:\n")
    print(text_prompt)
    print("\n\nThis is the output report:")
    print(report)
    print(f"\nTime elapsed: {time_elapsed} seconds")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process an audio file and generate a report.")
    parser.add_argument("--audio_file", type=str, help="Path to the audio file",
                        default=os.path.join(os.getenv("HOME"), "Downloads/secao_3.mpeg"))
    args = parser.parse_args()

    main(audio_path=args.audio_file)
