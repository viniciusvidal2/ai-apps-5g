# SOURCE repo: https://github.com/ollama/ollama-python/tree/main
from ollama import chat
from ollama import ChatResponse

# region single message and wait for response
response: ChatResponse = chat(model='llama3.2', messages=[
    {
        'role': 'user',
        'content': 'Why is the sky blue?',
    },
])
print(response['message']['content'])
# or access fields directly from the response object
print(response.message.content)
# endregion

# region stream messages
stream = chat(
    model='llama3.2',
    messages=[{'role': 'user',
               'content': 'me gere um reporte sobre a historia do brasil por favor'}],
    stream=True,
)

for chunk in stream:
    print(chunk['message']['content'], end='', flush=True)
# endregion

# region Client
# from ollama import Client
# client = Client(
#   host='http://localhost:11434',
#   headers={'x-some-header': 'some-value'}
# )
# response = client.chat(model='llama3.2', messages=[
#   {
#     'role': 'user',
#     'content': 'Why is the sky blue?',
#   },
# ])
# endregion

# region async client
# import asyncio
# from ollama import AsyncClient

# async def chat():
#   message = {'role': 'user', 'content': 'Why is the sky blue?'}
#   async for part in await AsyncClient().chat(model='llama3.2', messages=[message], stream=True):
#     print(part['message']['content'], end='', flush=True)

# asyncio.run(chat())
# endregion
