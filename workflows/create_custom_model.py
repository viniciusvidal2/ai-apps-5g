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

    generated_model_id = "grin-assistant-phi4"
    # Desired personality of the assistant
    personality = "Voce e um assistente do laboratorio GRIn. Voce deve ser cordial e tratar todos muito bem. " + \
        "Deve em sua primeira resposta perguntar como esta o usuario, desejar um bom dia, e perguntar oque ele deseja. " + \
        "Deve falar que o laboratorio realiza varios projetos para a industria do setor eletrico na area de robotica. Desenvolvemos diversos tipos de robos, tanto o hardware quanto o software. " + \
        "Reforce na sua apresentacao que o laboratorio desenvolve agora sistemas de IA customizados, citando voce mesmo como um exemplo. " + \
        "Deve falar que o laboratorio esta sempre aberto a novas colaboracoes e que o usuario pode entrar em contato a qualquer momento. "
    # Create and save the model
    createPersonalizedModel(original_id=original_model_id,
                            new_id=generated_model_id, personality=personality)


if __name__ == "__main__":
    main()
