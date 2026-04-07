import os
import cv2
import subprocess
from ultralytics import YOLO

# ====== CONFIGURAÇÃO DO STATUS DE EPI ======
# Ajuste conforme os nomes do seu modelo: print(model.names) para conferir.
REQUIRED_PPE_NAMES = ["0", "1", "2", "3", "4", "5", "6"]  # ex: ["helmet","vest","gloves","mask"]
PERSON_NAME = "9"

# Associação EPI -> pessoa (centro do bbox do EPI dentro do bbox da pessoa)
USE_CENTER_CONTAINMENT = True

# Thresholds
CONF_PERSON = 0.25
CONF_PPE = 0.25
IOU_THRESHOLD = 0.15  # usado se USE_CENTER_CONTAINMENT = False

def select_items(files, title):
    print(f"\n--- Selecione o(s) {title} ---")
    for i, f in enumerate(files):
        print(f"{i+1}. {f}")
    print(f"{len(files)+1}. Todos")

    choice = input("Digite o numero (virgula p/ multiplos, ex: 1,2): ").strip()
    selected = []
    if str(len(files) + 1) in choice.split(',') or choice.lower() == 'todos':
        return files
    for idx in choice.split(','):
        idx = idx.strip()
        if idx.isdigit():
            j = int(idx) - 1
            if 0 <= j < len(files):
                selected.append(files[j])
    return selected

def xyxy_to_int(box):
    x1, y1, x2, y2 = box
    return int(x1), int(y1), int(x2), int(y2)

def center_inside(ppe_xyxy, person_xyxy):
    px1, py1, px2, py2 = ppe_xyxy
    cx = (px1 + px2) / 2.0
    cy = (py1 + py2) / 2.0
    x1, y1, x2, y2 = person_xyxy
    return (x1 <= cx <= x2) and (y1 <= cy <= y2)

def iou(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    iw = max(0.0, inter_x2 - inter_x1)
    ih = max(0.0, inter_y2 - inter_y1)
    inter = iw * ih
    area_a = max(0.0, (ax2 - ax1)) * max(0.0, (ay2 - ay1))
    area_b = max(0.0, (bx2 - bx1)) * max(0.0, (by2 - by1))
    union = area_a + area_b - inter + 1e-9
    return inter / union

def get_class_ids_by_name(names_dict, wanted_names):
    # names_dict: {id: "name"}
    name_to_id = {v: k for k, v in names_dict.items()}
    ids = []
    for n in wanted_names:
        if n in name_to_id:
            ids.append(name_to_id[n])
    return ids

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    modelos_dir = os.path.join(base_dir, 'Modelos')
    video_dir = os.path.join(base_dir, 'Video')
    output_dir = os.path.join(base_dir, 'Output')
    os.makedirs(output_dir, exist_ok=True)

    # Tracker
    print("--- Selecione o Tracker ---")
    print("1. ByteTrack (rápido)")
    print("2. BoT-SORT (mais robusto)")
    t_choice = input("Digite 1 ou 2: ").strip()
    tracker = "bytetrack.yaml" if t_choice != "2" else "botsort.yaml"

    # Modelos
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

    # Vídeos
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

    print("\nIniciando...")

    for model_name in selected_models:
        model_path = os.path.join(modelos_dir, model_name)
        print(f"\n>>> Carregando modelo: {model_name} <<<")
        model = YOLO(model_path)

        # Descobre IDs das classes pelo nome
        names = model.names  # dict {id: name}
        person_ids = get_class_ids_by_name(names, [PERSON_NAME])
        ppe_ids = get_class_ids_by_name(names, REQUIRED_PPE_NAMES)

        if not person_ids:
            print(f"[ERRO] O modelo não tem a classe '{PERSON_NAME}'. Classes: {list(names.values())}")
            continue
        if not ppe_ids:
            print(f"[AVISO] Nenhuma EPI encontrada dentre {REQUIRED_PPE_NAMES}. Classes: {list(names.values())}")
            print("        Mesmo assim vou rodar (vai marcar todo mundo como NOT OK).")

        person_id = person_ids[0]

        for video_name in selected_videos:
            video_path = os.path.join(video_dir, video_name)
            v_name_no_ext, v_ext = os.path.splitext(video_name)
            m_name_no_ext, _ = os.path.splitext(model_name)

            output_filename = f"{v_name_no_ext}_{m_name_no_ext}_TRACK_STATUS{v_ext}"
            output_path = os.path.join(output_dir, output_filename)

            print(f"\n=> Vídeo [{video_name}] | Modelo [{model_name}] | Tracker [{tracker}]")

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

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # 1) TRACK só das pessoas (para ter ID)
                r_person = model.track(
                    source=frame,
                    persist=True,
                    tracker=tracker,
                    verbose=False,
                    conf=CONF_PERSON,
                    classes=[person_id],
                )[0]

                # 2) DETECÇÃO das EPIs (sem tracking)
                r_ppe = model.predict(
                    source=frame,
                    verbose=False,
                    conf=CONF_PPE,
                    classes=ppe_ids if ppe_ids else None
                )[0]

                # Extrai pessoas rastreadas
                persons = []
                if r_person.boxes is not None and len(r_person.boxes) > 0:
                    boxes_xyxy = r_person.boxes.xyxy.cpu().numpy()
                    ids = None
                    if r_person.boxes.id is not None:
                        ids = r_person.boxes.id.cpu().numpy().astype(int)
                    else:
                        # se não tiver id por algum motivo, cria fake incremental (não ideal)
                        ids = list(range(len(boxes_xyxy)))

                    for i, b in enumerate(boxes_xyxy):
                        persons.append({
                            "track_id": int(ids[i]),
                            "xyxy": b,
                            "ppe": {n: False for n in REQUIRED_PPE_NAMES}
                        })

                # Extrai EPIs
                ppes = []
                if r_ppe.boxes is not None and len(r_ppe.boxes) > 0:
                    ppe_xyxy = r_ppe.boxes.xyxy.cpu().numpy()
                    ppe_cls = r_ppe.boxes.cls.cpu().numpy().astype(int)
                    for b, c in zip(ppe_xyxy, ppe_cls):
                        ppes.append({"xyxy": b, "name": names[int(c)]})

                # 3) Associação EPI -> pessoa
                for ppe in ppes:
                    for person in persons:
                        if USE_CENTER_CONTAINMENT:
                            ok = center_inside(ppe["xyxy"], person["xyxy"])
                        else:
                            ok = iou(ppe["xyxy"], person["xyxy"]) > IOU_THRESHOLD
                        if ok and ppe["name"] in person["ppe"]:
                            person["ppe"][ppe["name"]] = True

                # 4) Desenho: pessoa + ID + status
                annotated = frame.copy()

                # Primeiro: Desenhar as caixas das EPIs encontradas para visualizacao
                for ppe in ppes:
                    px1, py1, px2, py2 = xyxy_to_int(ppe["xyxy"])
                    cv2.rectangle(annotated, (px1, py1), (px2, py2), (255, 255, 0), 1) # Ciano/Amarelo para EPI
                    cv2.putText(annotated, ppe["name"], (px1, max(0, py1 - 4)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1, cv2.LINE_AA)

                # Segundo: Desenhar as pessoas e listar o status delas
                for person in persons:
                    x1, y1, x2, y2 = xyxy_to_int(person["xyxy"])

                    missing = [k for k, v in person["ppe"].items() if not v]
                    present = [k for k, v in person["ppe"].items() if v]
                    is_ok = (len(missing) == 0) and (len(REQUIRED_PPE_NAMES) > 0)

                    # cor: verde ok / vermelho not ok
                    color = (0, 255, 0) if is_ok else (0, 0, 255)

                    cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

                    if len(REQUIRED_PPE_NAMES) == 0:
                        label_1 = f"ID {person['track_id']} | OK"
                        label_2 = ""
                    else:
                        # Exibe OK: e Falta:
                        str_ok = ",".join(present) if present else "Nenhum"
                        label_1 = f"ID {person['track_id']} | OK: {str_ok}"
                        label_2 = "" if is_ok else f"FALTA: {','.join(missing)}"

                    # Desenho do fundo do texto adaptativo para 2 linhas
                    (tw1, th1), _ = cv2.getTextSize(label_1, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                    (tw2, th2), _ = cv2.getTextSize(label_2, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1) if label_2 else ((0, 0), 0)
                    
                    tw = max(tw1, tw2)
                    total_h = th1 + (th2 + 5 if label_2 else 0) + 10
                    
                    cv2.rectangle(annotated, (x1, max(0, y1 - total_h)), (x1 + tw + 6, y1), color, -1)
                    
                    # Linha 1 (OK)
                    cv2.putText(annotated, label_1, (x1 + 3, y1 - (th2 + 8 if label_2 else 5)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                    
                    # Linha 2 (FALTA)
                    if label_2:
                        cv2.putText(annotated, label_2, (x1 + 3, y1 - 3),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

                out.write(annotated)

                current_frame += 1
                if total_frames > 0 and (current_frame % 5 == 0 or current_frame == total_frames):
                    percent = (current_frame / total_frames) * 100
                    print(f"  Progresso: {current_frame}/{total_frames} ({percent:.1f}%)", end='\r')

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

            print(f"  [Concluído] Salvo em: {output_path}")

if __name__ == "__main__":
    main()