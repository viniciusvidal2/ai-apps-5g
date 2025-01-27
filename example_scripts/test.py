from transformers import AutoModelForCausalLM, AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen-2")
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen-2", device_map="auto")

inputs = tokenizer("Hello, Qwen2! Write me a report on how 3d Point Clouds and how to apply filters in it", return_tensors="pt").to("cuda")
outputs = model.generate(**inputs, max_new_tokens=500)
print(tokenizer.decode(outputs[0]))
