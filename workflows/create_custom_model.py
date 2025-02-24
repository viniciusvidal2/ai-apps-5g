import os
import sys

# Add the parent directory folder to find our modules
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(root_path)

from ai_apis.customize_model import createPersonalizedModel
from ai_apis.pull_model_ollama import pullModel


def main() -> None:
    # Pull the model
    original_model_id = "phi4"
    result = pullModel(original_model_id)
    print(f"Pulling model succeeded: {result}")

    generated_model_id = "sae-assistant-phi4"
    # Desired personality of the assistant
    personality = "Eu sou um assistente para a empresa Santo Antonio Energia (SAE). Eu sempre me apresento inicialmente falando isso para o usuário. Devo ser sempre educado e prestativo." + \
        " Devo usar linguagem formal. Devo perguntar ao usuário se ele prefere ser chamado de 'senhor' ou 'senhora' para me referir a ele." + \
        " Devo sempre agradecer ao usuário por qualquer informação que ele me fornecer. Devo sempre me despedir do usuário de forma educada." + \
        " Devo falar inicialmente que sou capaz de fornecer relatórios fomatados, resumos, e conversar sobre as necessidades da tarefa que ele precisa de ajuda no contexto do trabalho."
    # Create and save the model
    createPersonalizedModel(original_id=original_model_id,
                            new_id=generated_model_id, personality=personality)


if __name__ == "__main__":
    main()
