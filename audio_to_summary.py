import os
import time
from ai_apis.bart import runBartSummarizer
from ai_apis.whisper import runWhisper


def main():
    # Measuring time
    start_time = time.time()
    # Define paths and model ids
    audio_path = os.path.join(os.getenv("HOME"), "Downloads/secao_3.mpeg")
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
    print(summary[0]['summary_text'])
    print(f"\nTime elapsed: {time_elapsed} seconds")


if __name__ == "__main__":
    main()
