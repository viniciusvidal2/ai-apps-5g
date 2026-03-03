from roboflow import Roboflow

# 🔑 Substitua pela sua API Key
API_KEY = "HrNilTBnc90zIXwyZsfA"

rf = Roboflow(api_key=API_KEY)

# 🗂 Workspace e projeto conforme sua URL
workspace = "iagos-workspace"
project_name = "epi-2-sem-no"

# 🆚 Número da versão que você quer baixar (ex: 1, 2, 3...)
version_number = 2

project = rf.workspace(workspace).project(project_name)
dataset = project.version(version_number).download("yolov8")

print("Download concluído.")
print("Arquivos salvos em:", dataset.location)