import os
import cv2
import subprocess
from ultralytics import YOLO

def select_items(files, title):
    print(f"\n--- Selecione o(s) {title} ---")
    for i, f in enumerate(files):
        print(f"{i+1}. {f}")
    print(f"{len(files)+1}. Todos")

    choice = input("Digite o numero da sua escolha (separado por virgula para multiplos, ex: 1,2): ").strip()

    selected = []
    if str(len(files) + 1) in choice.split(',') or choice.lower() == 'todos':
        selected = files
    else:
        for idx in choice.split(','):
            idx = idx.strip()
            if idx.isdigit():
                j = int(idx) - 1
                if 0 <= j < len(files):
                    selected.append(files[j])
    return selected


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    modelos_dir = os.path.join(base_dir, 'Modelos')
    video_dir = os.path.join(base_dir, 'Video')
    output_dir = os.path.join(base_dir, 'Output')
    os.makedirs(output_dir, exist_ok=True)

    # 0) Escolher tracker
    print("--- Selecione o Tracker ---")
    print("1. ByteTrack (recomendado - rápido e bom)")
    print("2. BoT-SORT (mais robusto, pode ser mais pesado)")
    t_choice = input("Digite 1 ou 2: ").strip()
    tracker = "bytetrack.yaml" if t_choice != "2" else "botsort.yaml"

    # 1) Carregar modelos
    if not os.path.exists(modelos_dir):
        print(f"Pasta '{modelos_dir}' não encontrada.")
        return

    modelos_files = [f for f in os.listdir(modelos_dir) if f.endswith(('.pt', '.engine', '.onnx'))]
    if not modelos_files:
        print("Nenhum modelo encontrado na pasta 'Modelos'.")
        return

    selected_models = select_items(modelos_files, "Modelo(s)")
    if not selected_models:
        print("Nenhum modelo valido selecionado.")
        return

    # 2) Carregar vídeos
    if not os.path.exists(video_dir):
        print(f"Pasta '{video_dir}' não encontrada.")
        return

    video_files = [f for f in os.listdir(video_dir) if f.endswith(('.mp4', '.avi', '.mov', '.mkv'))]
    if not video_files:
        print("Nenhum video encontrado na pasta 'Video'.")
        return

    selected_videos = select_items(video_files, "Video(s)")
    if not selected_videos:
        print("Nenhum video valido selecionado.")
        return

    print(f"\nModelos selecionados: {', '.join(selected_models)}")
    print(f"Videos selecionados: {', '.join(selected_videos)}")
    print(f"Tracker selecionado: {tracker}")
    print("\nIniciando o processamento...")

    for model_name in selected_models:
        model_path = os.path.join(modelos_dir, model_name)
        print(f"\n>>> Carregando modelo: {model_name} <<<")
        model = YOLO(model_path)

        for video_name in selected_videos:
            video_path = os.path.join(video_dir, video_name)
            v_name_no_ext, v_ext = os.path.splitext(video_name)
            m_name_no_ext, _ = os.path.splitext(model_name)

            output_filename = f"{v_name_no_ext}_{m_name_no_ext}_TRACK{v_ext}"
            output_path = os.path.join(output_dir, output_filename)

            print(f"\n=> Processando video [{video_name}] com o modelo [{model_name}] (TRACK)...")

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print(f"  [ERRO] Não abriu o vídeo: {video_path}")
                continue

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps == 0 or fps != fps:
                fps = 30

            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            if v_ext.lower() == '.avi':
                fourcc = cv2.VideoWriter_fourcc(*'XVID')

            temp_output_path = output_path.replace(v_ext, f"_temp{v_ext}")
            out = cv2.VideoWriter(temp_output_path, fourcc, fps, (width, height))

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            current_frame = 0

            # Dica importante:
            # persist=True mantém IDs do tracker ao longo do vídeo (estado interno).
            # tracker=... seleciona o algoritmo.
            # verbose=False evita spam.
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                results = model.track(
                    source=frame,
                    persist=True,
                    tracker=tracker,
                    verbose=False
                )

                # results[0].plot() já desenha caixas + (quando tracking ativo) IDs
                annotated_frame = results[0].plot()
                out.write(annotated_frame)

                current_frame += 1
                if total_frames > 0:
                    if current_frame % 5 == 0 or current_frame == total_frames:
                        percent = (current_frame / total_frames) * 100
                        print(f"  Progresso: Frame {current_frame}/{total_frames} ({percent:.1f}%)", end='\r')
                else:
                    if current_frame % 30 == 0:
                        print(f"  Processados: {current_frame} frames...", end='\r')

            cap.release()
            out.release()
            
            # Converte para reencodar em libx264 (suportado nativamente pelo Whatsapp/Browsers)
            print("\n  [Convertendo] Adequando o formato de compressão com FFmpeg (H.264)...")
            try:
                result = subprocess.run([
                    "ffmpeg", "-y", "-i", temp_output_path,
                    "-vcodec", "libx264", "-pix_fmt", "yuv420p",
                    output_path
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    os.remove(temp_output_path)
                else:
                    print(f"  [AVISO] Erro interno ffmpeg (mantendo mp4 padrão): {result.stderr.strip().split(chr(10))[-1]}")
                    if os.path.exists(output_path):
                        os.remove(output_path)
                    os.rename(temp_output_path, output_path)
            except Exception as e:
                print(f"  [AVISO] Nao foi possivel executar o programa local FFmpeg: {e}")
                if os.path.exists(temp_output_path):
                    os.rename(temp_output_path, output_path)

            print(f"  [Concluido] Salvo em: {output_path}")


if __name__ == "__main__":
    main()