import os
import time
from roboflow import Roboflow
from concurrent.futures import ThreadPoolExecutor, as_completed

# 🔑 API Key obtida do seu outro script
#API_KEY = "HrNilTBnc90zIXwyZsfA" iago.biundini@gmail.com
API_KEY = "mYNkfy6QOq4vGnLEeGCn"
WORKSPACE = "iagos-workspace"
PROJECT_NAME = "epi-with-person-kveck" # Altere este nome se você tiver criado um NOVO projeto para não misturar os dados

# Configurações de concorrência
MAX_WORKERS = 10  # Ajuste este valor dependendo da sua conexão e limites da API

def upload_single_image(args):
    """Função worker para upload de uma única imagem."""
    project, image_path, label_path, split, image_name = args
    try:
        # Envia a imagem e anotação
        project.upload(
            image_path=image_path,
            annotation_path=label_path,
            split=split,
            num_retry_uploads=3,
            is_prediction=False
        )
        return True, image_name, None
    except Exception as e:
        return False, image_name, str(e)

def main():
    print(f"Conectando ao Roboflow (Workspace: {WORKSPACE}, Projeto: {PROJECT_NAME})...")
    rf = Roboflow(api_key=API_KEY)
    
    # Seleciona o workspace e o projeto
    project = rf.workspace(WORKSPACE).project(PROJECT_NAME)
    
    # Caminho onde as novas imagens e labels estão armazenados
    dataset_dir = r"c:\Users\viki\Downloads\EPI\Person"
    #dataset_dir = r"c:\Users\viki\Downloads\EPI\EPI-2-(Sem-No)-2"
    
    splits = ["train", "valid", "test"]
    
    for split in splits:
        images_dir = os.path.join(dataset_dir, split, "images")
        labels_dir = os.path.join(dataset_dir, split, "labels")
        
        if not os.path.exists(images_dir):
            continue
            
        print(f"\n[{split.upper()}] Buscando imagens no diretório: {images_dir}")
        
        # Filtra apenas arquivos de imagem
        image_files = [f for f in os.listdir(images_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        total_images = len(image_files)
        
        if total_images == 0:
            print(f"Nenhum arquivo de imagem encontrado em {images_dir}.")
            continue
            
        print(f"Foram encontradas {total_images} imagens na pasta {split}. Iniciando upload em paralelo com {MAX_WORKERS} workers...")
        
        # Preparar argumentos para as threads
        upload_tasks = []
        for image_name in image_files:
            image_path = os.path.join(images_dir, image_name)
            label_name = os.path.splitext(image_name)[0] + ".txt"
            label_path = os.path.join(labels_dir, label_name)
            
            if not os.path.exists(label_path):
                label_path = None
                
            upload_tasks.append((project, image_path, label_path, split, image_name))
        
        sucesso = 0
        erros = 0
        
        # Iniciar pool de threads
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Enviar tarefas para execução
            futuros = {executor.submit(upload_single_image, task): task for task in upload_tasks}
            
            # Processar resultados conforme são concluídos
            for i, futuro in enumerate(as_completed(futuros), start=1):
                sucesso_upload, nome_imagem, msg_erro = futuro.result()
                if sucesso_upload:
                    sucesso += 1
                else:
                    erros += 1
                    print(f"\nErro em {nome_imagem}: {msg_erro}")
                
                # Imprimir status agrupado para não poluir o terminal
                if i % 10 == 0 or i == total_images:
                    print(f"Progresso: {i}/{total_images} | Sucesso: {sucesso} | Erros: {erros}", end='\r')
                    
        print(f"\n[{split.upper()}] Concluído: {sucesso} sucessos, {erros} erros.")

if __name__ == "__main__":
    start_time = time.time()
    main()
    print(f"\nTempo total: {time.time() - start_time:.2f} segundos")
