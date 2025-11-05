# ollama_models folder

Make sure you put your models here in the ollama standard, with the subfolders:

- __blobs/__: models chunks (sha256 confirmed)
- __manifests/registry.ollama.ai/library/__: models manifests description

As default from ollama, each model family has a subfolder inside the __library__ subfolder with its name, then the manifest should have the model size as its name.

Also, set all permissions for this folder so docker can use them to run the models:

```bash
sudo chmod -R 777 ollama_models
```
