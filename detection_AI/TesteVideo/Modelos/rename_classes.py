import os
from ultralytics import YOLO

def rename_classes():
    # Caminho do modelo
    base_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(base_dir, 'EPI_With_Person1.pt')  # Ajuste para o nome do seu modelo

    print(f"Carregando {model_path}...")
    model = YOLO(model_path)
    
    print("\nNomes de classe originais:")
    print(model.names)
    
    # Redefina o dicionário com os seus nomes reais em texto
    # IMPORTANTE: As chaves DEVEM mapear para as chaves numéricas que existem no dicionário original
    novos_nomes = {
        0: 'Nome_Classe_0',
        1: 'Nome_Classe_1',
        2: 'Nome_Classe_2',
        3: 'Nome_Classe_3',
        4: 'Nome_Classe_4',
        5: 'Nome_Classe_5',
        6: 'Nome_Classe_6',
        7: 'Person' # Você notou antes que a chave 7 tinha o valor '9' classificado do roboflow
    }
    
    # Atualiza internamente os nomes no modelo
    model.model.names = novos_nomes
    
    # Salva o modelo sobrepondo ou com um novo nome
    # O YOLO salva as variáveis atualizadas dentro do state_dict.
    novo_nome_pts = os.path.join(base_dir, 'EPI_With_Person1_Renomeado.pt')
    model.save(novo_nome_pts)
    
    print(f"\nModelo salvo como {novo_nome_pts}.")
    
    # Testar o carregamento do recém-criado
    print("\nTestando o carregamento do modelo novo:")
    model_teste = YOLO(novo_nome_pts)
    print(model_teste.names)

if __name__ == "__main__":
    rename_classes()
