import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import os


def runWhisper(model_id: str, audio_path: str) -> str:
    """Runs the whisper model on the given audio file.

    Args:
        model_id (str): the model id, for instance, "openai/whisper-large-v3-turbo"
        audio_path (str): the audio file path, preferably in .wav, .mpeg or .mp3 format

    Returns:
        str: the transcribed text
    """
    # Checks which device and variable types are available to create the model
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
    )
    model.to(device)
    processor = AutoProcessor.from_pretrained(model_id)

    # Creates the pipeline
    pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        torch_dtype=torch_dtype,
        device=device,
    )

    # Runs the pipeline and returns the transcribed text
    result = pipe(audio_path, return_timestamps=True)
    return result["text"]


if __name__ == "__main__":
    # Sample usage, runs if calling this script directly
    model_id = "openai/whisper-large-v3-turbo"
    audio_path = os.path.join(os.getenv("HOME"), "Downloads/secao_3.mpeg")
    print(runWhisper(model_id=model_id, audio_path=audio_path))
