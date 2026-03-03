import os
from ultralytics import YOLO

def main():
    # Obtem a pasta onde o script atual está (neste caso, a pasta Modelos)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Encontra todos os arquivos de modelo na pasta
    modelos_files = [f for f in os.listdir(base_dir) if f.endswith(('.pt', '.engine', '.onnx'))]
    
    if not modelos_files:
        print("Nenhum modelo encontrado na pasta Modelos.")
        return
        
    for model_name in modelos_files:
        model_path = os.path.join(base_dir, model_name)
        print(f"\n--- Classes do modelo: {model_name} ---")
        try:
            model = YOLO(model_path)
            # model.names é um dicionário onde a chave é o ID e o valor é o nome da classe
            for class_id, class_name in model.names.items():
                print(f"ID {class_id}: {class_name}")
        except Exception as e:
            print(f"Erro ao carregar o modelo {model_name}: {e}")

if __name__ == "__main__":
    main()
