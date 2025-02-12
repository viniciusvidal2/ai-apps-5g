# Models folder

Make sure you put your models here in the ollama format, in subfolders:
- blobs: models chunks
- manifests: models description

You should see you model names clearly in the manifests folder. Also set all permissions for this folder so docker can use them to run the models:

```bash
sudo chmod -R 777 ollama_models
```
