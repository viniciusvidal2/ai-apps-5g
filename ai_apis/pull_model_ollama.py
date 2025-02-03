from tqdm import tqdm
from ollama import pull

def pull_model(model_id: str) -> bool:
    """Pulls the model while showing progress bars.

    Args:
        model_id (str): the model id we are interested in

    Returns:
        bool: True if downloaded succeeded
    """
    try:
        current_digest, bars = '', {}
        for progress in pull(model=model_id, stream=True):
            digest = progress.get('digest', '')
            if digest != current_digest and current_digest in bars:
                bars[current_digest].close()

            if not digest:
                print(progress.get('status'))
                continue

            if digest not in bars and (total := progress.get('total')):
                bars[digest] = tqdm(total=total, desc=f'pulling {digest[7:19]}', unit='B', unit_scale=True)

            if completed := progress.get('completed'):
                bars[digest].update(completed - bars[digest].n)

            current_digest = digest
        return True
    except Exception as e:
        print(f"Error pulling model {model_id}: {e}")
        return False

if __name__ == "__main__":
    # Run a sample of the script for demonstration purposes
    result = pull_model("phi4")
    print(f"Pulling model succeeded: {result}")
