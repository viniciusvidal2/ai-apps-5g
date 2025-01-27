import transformers
from time import time

start = time()
pipeline = transformers.pipeline(
    "text-generation",
    model="microsoft/phi-4",
    model_kwargs={"torch_dtype": "auto"},
    device_map="auto",
)

messages = [
    {"role": "system", "content": "You are a chatbot that must provide improved reports from the text the user inserts."},
    {"role": "user", "content": "make a report of 3d point clouds and how to filter them in terms of voxels and outliers. Use topics."},
]

outputs = pipeline(messages, max_new_tokens=128)
print(outputs[0]["generated_text"][-1])
end = time()
print(f"Time taken: {end - start} seconds.")
