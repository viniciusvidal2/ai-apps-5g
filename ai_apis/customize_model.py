from ollama import Client


def createPersonalizedModel(original_id: str, new_id: str, personality: str) -> None:
    """Creates a personalized model based on an original model with a given personality

    Args:
        original_id (str): the id of the original model
        new_id (str): the id of the new model
        personality (str): the personality of the new model
    """
    client = Client()
    response = client.create(
        model=new_id,
        from_=original_id,
        system=personality,
        stream=False,
    )
    print(response.status)


if __name__ == "__main__":
    original_model_id = "deepseek-r1:14b"
    generated_model_id = "sae-assistant"
    # Desired personality of the assistant
    personality = "Eu sou um assistente para a empresa Santo Antonio Energia (SAE). Eu sempre me apresento inicialmente falando isso para o usuário. Devo ser sempre educado e prestativo." + \
        " Devo usar linguagem formal. Devo perguntar ao usuário se ele prefere ser chamado de 'senhor' ou 'senhora' para me referir a ele." + \
        " Devo sempre agradecer ao usuário por qualquer informação que ele me fornecer. Devo sempre me despedir do usuário de forma educada." + \
        " Devo falar inicialmente que sou capaz de fornecer relatórios fomatados, resumos, e conversar sobre as necessidades da tarefa que ele precisa de ajuda no contexto do trabalho." 
    # Create and save the model
    createPersonalizedModel(original_id=original_model_id,
                            new_id=generated_model_id, personality=personality)
