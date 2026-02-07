from ollama import Client
import os
import shutil
import json


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


def copyModel(model_id: str) -> bool:
    """Creates a copy of a model to be used in the docker application

    Args:
        model_id (str): the id of the model to be copied

    Returns:
        bool: True if the model was copied successfully, False otherwise
    """
    # Usual paths where ollama stores the models
    user = os.getenv("USER")
    likely_paths = [
        f"/home/{user}/.ollama/models",
        "/usr/share/ollama/.ollama/models",]
    # The blobs and manifest paths inside the models folder
    manifest_relative_path = os.path.join(
        "manifests", "registry.ollama.ai", "library", model_id)
    blobs_relative_path = "blobs"
    # The destination should be the ollama_models folder in the root of the project
    root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    destination_path = os.path.join(root_path, "ollama_models")

    for path in likely_paths:
        manifests_path = os.path.join(path, manifest_relative_path)
        if os.path.exists(manifests_path):
            # Copy the model latest manifests folder to the destination
            os.makedirs(os.path.join(destination_path,
                        manifest_relative_path), exist_ok=True)
            shutil.copytree(manifests_path, os.path.join(
                destination_path, manifest_relative_path), dirs_exist_ok=True)
            
            # Read the latest manifest file as a json
            manifest_file = os.path.join(
                destination_path, manifest_relative_path, "latest")
            with open(manifest_file, "r") as file:
                manifest = json.load(file)

            # Get the specific blobs we need to copy
            blobs = manifest["layers"]
            # Copy the blobs to the destination
            os.makedirs(os.path.join(destination_path, "blobs"), exist_ok=True)
            for blob in blobs:
                blob_name_split = blob["digest"].split(":")
                blob_name = blob_name_split[0] + "-" + blob_name_split[1]
                blob_path = os.path.join(
                    path, blobs_relative_path, blob_name)
                shutil.copyfile(blob_path, os.path.join(
                    destination_path, blobs_relative_path, blob_name))
                
            return True

    return False


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
    # Copy the generated model to our folder
    result = copyModel(generated_model_id)
    if result:
        print("Model created and copied successfully")
    else:
        print("Model not found in the usual paths")
