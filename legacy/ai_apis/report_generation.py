from ollama import chat


def generateReportWithModel(model_id: str, message: str) -> str:
    """Generates a report with a given model and message.

    Args:
        model_id (str): the model id we are interested in
        message (str): the message to generate the report

    Returns:
        str: the generated report
    """
    messages = [
        {
            'role': 'user',
            'content': 'Gere um relatório completo reference ao meu pŕoximo prompt. O relatório deve conter introdução, corpo e conclusão.',
        },
        {
            'role': 'assistant',
            'content': "Estou aguardando o próximo prompt, farei as seções, e utilizarei tópicos e subseções quando necessário.",
        },
        {
            'role': 'user',
            'content': message,
        }
    ]
    response = chat(
        model=model_id,
        messages=messages
    )

    return response['message']['content']


if __name__ == "__main__":
    # Run a sample of the script for demonstration purposes
    result = generateReportWithModel(
        "llama3.2", "O que é inteligência artificial?")
    print("Generated report:\n")
    print(f"{result}")
