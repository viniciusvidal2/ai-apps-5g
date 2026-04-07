from __future__ import annotations

import argparse
import contextlib
import shutil
import sys
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

if sys.platform == "win32" and sys.version_info >= (3, 13):
    raise SystemExit(
        "Python 3.13 no Windows esta carregando um build experimental do NumPy neste ambiente, "
        "o que interrompe o script antes da execucao.\n"
        "Use Python 3.12 para este projeto e reinstale as dependencias nesse ambiente.\n"
        "Exemplo:\n"
        "  C:\\Users\\viki\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m venv .venv\n"
        "  .\\.venv\\Scripts\\activate\n"
        "  python -m pip install --upgrade pip\n"
        "  python -m pip install numpy==1.26.4 opencv-python ultralytics pillow huggingface_hub gdown einops pycocotools\n"
        "  python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128\n"
        "  python -m pip install -e .\\sam3"
    )

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
SAM3_REPO_ROOT = PROJECT_ROOT / "sam3"
ASSETS_DIR = SAM3_REPO_ROOT / "Arquivos"
LOCAL_CHECKPOINT = SAM3_REPO_ROOT / "Arquivos" / "sam3.pt"
LOCAL_BPE = SAM3_REPO_ROOT / "sam3" / "assets" / "bpe_simple_vocab_16e6.txt.gz"
GOOGLE_DRIVE_ASSETS_URL = "https://drive.google.com/drive/folders/1byYXgr1HlUKzzz5wMgnaXj4MxZeptalt?usp=sharing"

if SAM3_REPO_ROOT.exists():
    sys.path.insert(0, str(SAM3_REPO_ROOT))


DEFAULT_PPE_PROMPTS = ["helmet", "safety vest", "gloves", "glasses"]
DEFAULT_SOURCE = SAM3_REPO_ROOT / "video" / "Teste.mp4"
DEFAULT_YOLO_WEIGHTS = PROJECT_ROOT / "yolov8n.pt"
DEFAULT_TRACKER = "bytetrack.yaml"
DEFAULT_PERSON_CONF = 0.35
DEFAULT_SAM_THRESHOLD = 0.20
DEFAULT_SAM_SCORE_THRESHOLD = 0.30
DEFAULT_INFER_WIDTH = 1024
DEFAULT_PERSON_PADDING = 0.12
DEFAULT_MAX_UPSCALE = 2.5
DEFAULT_DISPLAY_WIDTH = 1400
DEFAULT_OUTPUT_VIDEO = Path("outputs") / "segment_yolo_sam_window.mp4"
DEFAULT_DEVICE = "auto"
DEFAULT_PANEL_WIDTH = 420
DEFAULT_MAX_PANEL_PEOPLE = 4
DEFAULT_MAX_MISSED_FRAMES = 90


@dataclass
class PersonState:
    track_id: int
    first_seen_frame: int
    ppe_status: dict[str, bool] = field(default_factory=dict)
    ppe_scores: dict[str, float] = field(default_factory=dict)
    latest_crop_bgr: np.ndarray | None = None
    latest_bbox: tuple[int, int, int, int] | None = None
    analyzed: bool = False
    last_seen_frame: int = 0

    @property
    def has_all_ppe(self) -> bool:
        return bool(self.ppe_status) and all(self.ppe_status.values())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="YOLO track para pessoa + SAM3 para verificar EPI em arquivo de video."
    )
    parser.add_argument(
        "--source",
        default=str(DEFAULT_SOURCE),
        help="Caminho do arquivo de video que sera usado como fonte.",
    )
    parser.add_argument(
        "--yolo-weights",
        default=str(DEFAULT_YOLO_WEIGHTS),
        help="Pesos do YOLO usados para tracking de pessoa.",
    )
    parser.add_argument(
        "--tracker",
        default=DEFAULT_TRACKER,
        help="Tracker do Ultralytics. Ex: bytetrack.yaml ou botsort.yaml",
    )
    parser.add_argument(
        "--ppe-prompts",
        default="helmet,safety vest,gloves,glasses",
        help='Prompts do SAM3 separados por virgula. Ex: "helmet,safety vest,gloves,glasses"',
    )
    parser.add_argument(
        "--person-conf",
        type=float,
        default=DEFAULT_PERSON_CONF,
        help="Confianca minima do YOLO para pessoa.",
    )
    parser.add_argument(
        "--sam-threshold",
        type=float,
        default=DEFAULT_SAM_THRESHOLD,
        help="Threshold de confianca do SAM3.",
    )
    parser.add_argument(
        "--sam-score-threshold",
        type=float,
        default=DEFAULT_SAM_SCORE_THRESHOLD,
        help="Score minimo final para marcar um EPI como presente.",
    )
    parser.add_argument(
        "--infer-width",
        type=int,
        default=DEFAULT_INFER_WIDTH,
        help="Largura usada na inferencia do SAM3 no recorte da pessoa.",
    )
    parser.add_argument(
        "--person-padding",
        type=float,
        default=DEFAULT_PERSON_PADDING,
        help="Padding percentual aplicado ao redor da caixa da pessoa antes do SAM3.",
    )
    parser.add_argument(
        "--max-upscale",
        type=float,
        default=DEFAULT_MAX_UPSCALE,
        help="Limita o upscale do recorte da pessoa antes do SAM3.",
    )
    parser.add_argument(
        "--display-width",
        type=int,
        default=DEFAULT_DISPLAY_WIDTH,
        help="Largura total da janela exibida.",
    )
    parser.add_argument(
        "--save-output-video",
        action="store_true",
        help="Salva em video a janela final completa: principal + painel lateral.",
    )
    parser.add_argument(
        "--output-video",
        type=Path,
        default=DEFAULT_OUTPUT_VIDEO,
        help="Caminho do video salvo quando --save-output-video estiver ativo.",
    )
    parser.add_argument(
        "--device",
        default=DEFAULT_DEVICE,
        choices=["auto", "cuda", "cpu"],
        help="Dispositivo para inferencia.",
    )
    parser.add_argument(
        "--panel-width",
        type=int,
        default=DEFAULT_PANEL_WIDTH,
        help="Largura da coluna lateral com as pessoas e seus EPI's.",
    )
    parser.add_argument(
        "--max-panel-people",
        type=int,
        default=DEFAULT_MAX_PANEL_PEOPLE,
        help="Numero maximo de pessoas mostradas na lateral.",
    )
    parser.add_argument(
        "--max-missed-frames",
        type=int,
        default=DEFAULT_MAX_MISSED_FRAMES,
        help="Remove pessoas nao vistas por N frames.",
    )
    return parser


def ensure_dependencies() -> None:
    missing = []
    try:
        import cv2  # noqa: F401
    except ModuleNotFoundError:
        missing.append("opencv-python")
    try:
        import torch  # noqa: F401
    except ModuleNotFoundError:
        missing.append("torch")
    try:
        import huggingface_hub  # noqa: F401
    except ModuleNotFoundError:
        missing.append("huggingface_hub")
    try:
        import ultralytics  # noqa: F401
    except ModuleNotFoundError:
        missing.append("ultralytics")
    try:
        import PIL  # noqa: F401
    except ModuleNotFoundError:
        missing.append("pillow")
    try:
        import einops  # noqa: F401
    except ModuleNotFoundError:
        missing.append("einops")
    try:
        import pycocotools  # noqa: F401
    except ModuleNotFoundError:
        missing.append("pycocotools")

    if missing:
        raise SystemExit(
            "Dependencias ausentes:\n"
            "  pip install " + " ".join(missing) + "\n"
            "  pip install -e .\\sam3"
        )


def ensure_sam_assets() -> None:
    if ASSETS_DIR.exists() and LOCAL_CHECKPOINT.exists():
        return

    try:
        import gdown
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "A pasta de assets do SAM3 nao foi encontrada e o pacote 'gdown' nao esta instalado.\n"
            "Instale as dependencias com:\n"
            "  pip install -r requirements.txt"
        ) from exc

    temp_root = SAM3_REPO_ROOT / "_downloads_tmp"
    download_dir = temp_root / "google_drive_assets"

    if temp_root.exists():
        shutil.rmtree(temp_root)
    temp_root.mkdir(parents=True, exist_ok=True)

    try:
        print(f"Assets do SAM3 nao encontrados em: {ASSETS_DIR}")
        print("Baixando pasta Arquivos do Google Drive...")
        gdown.download_folder(
            url=GOOGLE_DRIVE_ASSETS_URL,
            output=str(download_dir),
            quiet=False,
            remaining_ok=True,
        )

        extracted_dir = extract_archives_if_needed(download_dir)
        source_dir = locate_downloaded_assets_dir(extracted_dir)
        ASSETS_DIR.parent.mkdir(parents=True, exist_ok=True)

        if ASSETS_DIR.exists():
            shutil.rmtree(ASSETS_DIR)
        shutil.move(str(source_dir), str(ASSETS_DIR))
    except Exception as exc:
        raise SystemExit(f"Falha ao baixar/extrair os assets do SAM3: {exc}") from exc
    finally:
        if temp_root.exists():
            shutil.rmtree(temp_root, ignore_errors=True)

    if not LOCAL_CHECKPOINT.exists():
        raise SystemExit(
            f"Download concluido, mas o checkpoint esperado nao foi encontrado em: {LOCAL_CHECKPOINT}"
        )


def extract_archives_if_needed(download_dir: Path) -> Path:
    zip_files = sorted(download_dir.rglob("*.zip"))
    if not zip_files:
        return download_dir

    extracted_root = download_dir / "_extracted"
    extracted_root.mkdir(parents=True, exist_ok=True)
    for zip_path in zip_files:
        target_dir = extracted_root / zip_path.stem
        target_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zip_file:
            zip_file.extractall(target_dir)
    return extracted_root


def locate_downloaded_assets_dir(search_root: Path) -> Path:
    if (search_root / "sam3.pt").exists():
        return search_root

    candidate_dirs = sorted(
        path
        for path in search_root.rglob("*")
        if path.is_dir() and (path / "sam3.pt").exists()
    )
    if not candidate_dirs:
        raise FileNotFoundError(
            "Nao encontrei uma pasta contendo 'sam3.pt' dentro do download do Google Drive."
        )
    return candidate_dirs[0]


def parse_prompts(prompt_text: str) -> list[str]:
    prompts = [part.strip() for part in prompt_text.replace(";", ",").split(",")]
    prompts = [prompt for prompt in prompts if prompt]
    if not prompts:
        return DEFAULT_PPE_PROMPTS.copy()
    return prompts


def describe_cuda_status() -> str:
    import torch

    return (
        f"python={sys.executable}\n"
        f"torch={torch.__version__}\n"
        f"torch_cuda_build={torch.version.cuda}\n"
        f"cuda_available={torch.cuda.is_available()}\n"
        f"device_count={torch.cuda.device_count()}"
    )


def pick_device(device_arg: str) -> str:
    import torch

    if device_arg == "cuda":
        if not torch.cuda.is_available():
            raise SystemExit(
                "CUDA foi solicitado, mas nao esta disponivel neste ambiente.\n"
                f"{describe_cuda_status()}\n"
                "Ative a .venv do projeto e reinstale o PyTorch com CUDA."
            )
        return "cuda"
    if device_arg == "cpu":
        return "cpu"
    if torch.cuda.is_available():
        return "cuda"
    print(
        "CUDA nao esta disponivel neste ambiente; seguindo com CPU.\n"
        f"{describe_cuda_status()}",
        file=sys.stderr,
    )
    return "cpu"


def build_sam_processor(device: str, threshold: float):
    import torch
    from sam3.model_builder import build_sam3_image_model
    from sam3.model.sam3_image_processor import Sam3Processor

    if not LOCAL_BPE.exists():
        raise SystemExit(f"Arquivo BPE nao encontrado: {LOCAL_BPE}")
    if not LOCAL_CHECKPOINT.exists():
        raise SystemExit(f"Checkpoint local nao encontrado: {LOCAL_CHECKPOINT}")

    model = build_sam3_image_model(
        device=device,
        bpe_path=str(LOCAL_BPE),
        checkpoint_path=str(LOCAL_CHECKPOINT),
        load_from_HF=False,
    )
    model = model.to(dtype=torch.float32)
    return Sam3Processor(model=model, device=device, confidence_threshold=threshold)


def build_yolo_model(weights: str):
    from ultralytics import YOLO

    return YOLO(weights)


def open_capture(source_text: str):
    import cv2

    source_path = Path(source_text).expanduser().resolve()
    if not source_path.exists():
        raise SystemExit(f"Video nao encontrado: {source_path}")
    if source_path.suffix.lower() not in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
        raise SystemExit(
            "No momento, `--source` precisa ser um arquivo de video "
            "(.mp4, .mov, .avi, .mkv ou .webm)."
        )

    cap = cv2.VideoCapture(str(source_path))
    if not cap.isOpened():
        raise SystemExit(f"Nao foi possivel abrir a fonte de video: {source_text}")
    return cap


def get_capture_fps(capture) -> float:
    import cv2

    fps = capture.get(cv2.CAP_PROP_FPS)
    return float(fps) if fps and fps > 0 else 30.0


def create_video_writer(output_path: Path, fps: float, frame_size: tuple[int, int]):
    import cv2

    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    writer = cv2.VideoWriter(
        str(output_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        frame_size,
    )
    if not writer.isOpened():
        raise SystemExit(f"Nao foi possivel criar o video de saida: {output_path}")
    return writer, output_path


def analyze_person_crop(
    processor,
    crop_bgr: np.ndarray,
    prompts: list[str],
    infer_width: int,
    score_threshold: float,
    max_upscale: float,
) -> tuple[dict[str, bool], dict[str, float]]:
    import cv2
    import torch
    from PIL import Image

    crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
    orig_h, orig_w = crop_rgb.shape[:2]
    target_width = max(64, infer_width)
    max_allowed_width = max(orig_w, int(round(orig_w * max(1.0, max_upscale))))
    infer_width = max(64, min(target_width, max_allowed_width))
    infer_height = max(64, int(round(orig_h * (infer_width / max(1, orig_w)))))
    infer_rgb = cv2.resize(
        crop_rgb,
        (infer_width, infer_height),
        interpolation=cv2.INTER_CUBIC if infer_width >= orig_w else cv2.INTER_AREA,
    )

    pil_image = Image.fromarray(infer_rgb)
    autocast_device = "cuda" if torch.cuda.is_available() else "cpu"
    cuda_guard = (
        torch.cuda.amp.autocast(enabled=False)
        if torch.cuda.is_available()
        else contextlib.nullcontext()
    )

    statuses: dict[str, bool] = {}
    scores_map: dict[str, float] = {}

    with torch.autocast(device_type=autocast_device, enabled=False), cuda_guard:
        for prompt in prompts:
            state = processor.set_image(pil_image)
            output = processor.set_text_prompt(prompt=prompt, state=state)
            scores = output["scores"].detach().cpu().numpy()
            best_score = float(scores.max()) if len(scores) else 0.0
            statuses[prompt] = best_score >= score_threshold
            scores_map[prompt] = best_score

    return statuses, scores_map


def clamp_bbox(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    frame_w: int,
    frame_h: int,
) -> tuple[int, int, int, int] | None:
    x0_i = max(0, min(frame_w - 1, int(round(x0))))
    y0_i = max(0, min(frame_h - 1, int(round(y0))))
    x1_i = max(0, min(frame_w - 1, int(round(x1))))
    y1_i = max(0, min(frame_h - 1, int(round(y1))))
    if x1_i <= x0_i or y1_i <= y0_i:
        return None
    return x0_i, y0_i, x1_i, y1_i


def expand_bbox(
    bbox: tuple[int, int, int, int],
    frame_w: int,
    frame_h: int,
    padding_ratio: float,
) -> tuple[int, int, int, int] | None:
    x0, y0, x1, y1 = bbox
    bw = x1 - x0
    bh = y1 - y0
    pad_x = int(round(bw * max(0.0, padding_ratio)))
    pad_y = int(round(bh * max(0.0, padding_ratio)))
    return clamp_bbox(
        x0 - pad_x,
        y0 - pad_y,
        x1 + pad_x,
        y1 + pad_y,
        frame_w=frame_w,
        frame_h=frame_h,
    )


def crop_person(frame_bgr: np.ndarray, bbox: tuple[int, int, int, int]) -> np.ndarray:
    x0, y0, x1, y1 = bbox
    return frame_bgr[y0:y1, x0:x1].copy()


def update_people_from_tracks(
    frame_bgr: np.ndarray,
    results,
    frame_index: int,
    people: dict[int, PersonState],
    processor,
    prompts: list[str],
    infer_width: int,
    person_padding: float,
    score_threshold: float,
    max_upscale: float,
) -> list[int]:
    frame_h, frame_w = frame_bgr.shape[:2]
    active_ids: list[int] = []

    if not results or results[0].boxes is None:
        return active_ids

    boxes = results[0].boxes
    xyxy = boxes.xyxy.cpu().numpy() if boxes.xyxy is not None else np.empty((0, 4))
    ids = boxes.id.int().cpu().tolist() if boxes.id is not None else []

    for idx, raw_box in enumerate(xyxy):
        if idx >= len(ids):
            continue
        track_id = int(ids[idx])
        bbox = clamp_bbox(*raw_box.tolist(), frame_w=frame_w, frame_h=frame_h)
        if bbox is None:
            continue
        padded_bbox = expand_bbox(
            bbox,
            frame_w=frame_w,
            frame_h=frame_h,
            padding_ratio=person_padding,
        )
        if padded_bbox is None:
            continue

        active_ids.append(track_id)
        crop_bgr = crop_person(frame_bgr, padded_bbox)
        if crop_bgr.size == 0:
            continue

        state = people.get(track_id)
        if state is None:
            state = PersonState(track_id=track_id, first_seen_frame=frame_index)
            people[track_id] = state

        state.latest_bbox = bbox
        state.latest_crop_bgr = crop_bgr
        state.last_seen_frame = frame_index

        if not state.analyzed:
            statuses, scores = analyze_person_crop(
                processor=processor,
                crop_bgr=crop_bgr,
                prompts=prompts,
                infer_width=infer_width,
                score_threshold=score_threshold,
                max_upscale=max_upscale,
            )
            state.ppe_status = statuses
            state.ppe_scores = scores
            state.analyzed = True

    return active_ids


def prune_missing_people(
    people: dict[int, PersonState],
    frame_index: int,
    max_missed_frames: int,
) -> None:
    stale_ids = [
        track_id
        for track_id, state in people.items()
        if frame_index - state.last_seen_frame > max_missed_frames
    ]
    for track_id in stale_ids:
        people.pop(track_id, None)


def draw_main_frame(
    frame_bgr: np.ndarray,
    people: dict[int, PersonState],
    active_ids: list[int],
    prompts: list[str],
    fps_text: str,
) -> np.ndarray:
    import cv2

    canvas = frame_bgr.copy()

    for track_id in active_ids:
        state = people.get(track_id)
        if state is None or state.latest_bbox is None:
            continue

        x0, y0, x1, y1 = state.latest_bbox
        if not state.analyzed:
            color = (0, 200, 255)
            title = f"Pessoa {track_id} | analisando..."
        elif state.has_all_ppe:
            color = (0, 200, 0)
            title = f"Pessoa {track_id} | EPI OK"
        else:
            missing = [prompt for prompt in prompts if not state.ppe_status.get(prompt, False)]
            color = (0, 0, 255)
            title = f"Pessoa {track_id} | falta: {', '.join(missing)}"

        cv2.rectangle(canvas, (x0, y0), (x1, y1), color, 2)
        cv2.putText(
            canvas,
            title,
            (x0, max(24, y0 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.60,
            color,
            2,
            cv2.LINE_AA,
        )

    cv2.rectangle(canvas, (10, 10), (420, 76), (20, 20, 20), -1)
    cv2.putText(
        canvas,
        fps_text,
        (20, 38),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        canvas,
        "YOLO track pessoa + SAM3 EPI | Q para sair",
        (20, 64),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        (220, 220, 220),
        1,
        cv2.LINE_AA,
    )

    return canvas


def fit_image_to_box(image_bgr: np.ndarray, box_w: int, box_h: int) -> np.ndarray:
    import cv2

    if box_w <= 0 or box_h <= 0:
        return np.zeros((1, 1, 3), dtype=np.uint8)

    img_h, img_w = image_bgr.shape[:2]
    scale = min(box_w / max(1, img_w), box_h / max(1, img_h))
    new_w = max(1, int(round(img_w * scale)))
    new_h = max(1, int(round(img_h * scale)))
    resized = cv2.resize(image_bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)

    canvas = np.full((box_h, box_w, 3), 28, dtype=np.uint8)
    x = (box_w - new_w) // 2
    y = (box_h - new_h) // 2
    canvas[y : y + new_h, x : x + new_w] = resized
    return canvas


def build_side_panel(
    active_ids: list[int],
    people: dict[int, PersonState],
    panel_width: int,
    panel_height: int,
    prompts: list[str],
    max_people: int,
) -> np.ndarray:
    import cv2

    panel = np.full((panel_height, panel_width, 3), 24, dtype=np.uint8)
    cv2.putText(
        panel,
        "Pessoas detectadas",
        (18, 32),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.85,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )

    visible_ids = active_ids[: max(1, max_people)]
    if not visible_ids:
        cv2.putText(
            panel,
            "Nenhuma pessoa com track ativo.",
            (18, 72),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (210, 210, 210),
            1,
            cv2.LINE_AA,
        )
        return panel

    top_margin = 52
    gap = 14
    available_h = panel_height - top_margin - gap
    card_h = max(140, (available_h - gap * (len(visible_ids) - 1)) // len(visible_ids))

    for idx, track_id in enumerate(visible_ids):
        state = people.get(track_id)
        if state is None:
            continue

        y0 = top_margin + idx * (card_h + gap)
        y1 = min(panel_height - 1, y0 + card_h)
        cv2.rectangle(panel, (10, y0), (panel_width - 10, y1), (42, 42, 42), -1)

        crop_h = max(72, card_h - 62)
        crop_w = max(100, int(panel_width * 0.42))
        if state.latest_crop_bgr is not None:
            crop_preview = fit_image_to_box(state.latest_crop_bgr, crop_w, crop_h)
        else:
            crop_preview = np.full((crop_h, crop_w, 3), 36, dtype=np.uint8)
        crop_y = y0 + 12
        crop_x = 18
        panel[crop_y : crop_y + crop_preview.shape[0], crop_x : crop_x + crop_preview.shape[1]] = crop_preview

        text_x = crop_x + crop_w + 16
        title = f"Pessoa {track_id}"
        title_color = (0, 220, 0) if state.has_all_ppe else (0, 170, 255) if not state.analyzed else (0, 0, 255)
        cv2.putText(
            panel,
            title,
            (text_x, y0 + 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            title_color,
            2,
            cv2.LINE_AA,
        )

        line_y = y0 + 56
        for prompt in prompts:
            ok = state.ppe_status.get(prompt, False)
            score = state.ppe_scores.get(prompt, 0.0)
            label = f"[OK] {prompt} ({score:.2f})" if ok else f"[X] {prompt}"
            color = (0, 210, 0) if ok else (0, 0, 255)
            cv2.putText(
                panel,
                label,
                (text_x, line_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.52,
                color,
                1,
                cv2.LINE_AA,
            )
            line_y += 24

        overall = "Todos os EPI's" if state.has_all_ppe else "EPI incompleto"
        overall_color = (0, 220, 0) if state.has_all_ppe else (0, 0, 255)
        cv2.putText(
            panel,
            overall,
            (text_x, min(y1 - 12, line_y + 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.62,
            overall_color,
            2,
            cv2.LINE_AA,
        )

    return panel


def compose_display(
    main_frame: np.ndarray,
    side_panel: np.ndarray,
    display_width: int,
) -> np.ndarray:
    import cv2

    combined = np.concatenate([main_frame, side_panel], axis=1)
    if display_width <= 0 or combined.shape[1] == display_width:
        return combined
    scale = display_width / combined.shape[1]
    display_height = max(1, int(round(combined.shape[0] * scale)))
    return cv2.resize(combined, (display_width, display_height), interpolation=cv2.INTER_AREA)


def main() -> None:
    ensure_dependencies()
    ensure_sam_assets()
    parser = build_parser()
    args = parser.parse_args()

    import cv2

    prompts = parse_prompts(args.ppe_prompts)
    device = pick_device(args.device)

    print(f"Usando device: {device}")
    print(f"Prompts EPI: {', '.join(prompts)}")
    print("Carregando YOLO e SAM3...")

    yolo_model = build_yolo_model(args.yolo_weights)
    sam_processor = build_sam_processor(device=device, threshold=args.sam_threshold)
    capture = open_capture(args.source)
    source_fps = get_capture_fps(capture)
    output_writer = None
    output_path = None

    people: dict[int, PersonState] = {}
    frame_index = 0
    smoothed_fps = 0.0

    while True:
        loop_start = time.perf_counter()
        ok, frame_bgr = capture.read()
        if not ok:
            break

        yolo_results = yolo_model.track(
            source=frame_bgr,
            persist=True,
            classes=[0],
            conf=args.person_conf,
            verbose=False,
            tracker=args.tracker,
        )

        active_ids = update_people_from_tracks(
            frame_bgr=frame_bgr,
            results=yolo_results,
            frame_index=frame_index,
            people=people,
            processor=sam_processor,
            prompts=prompts,
            infer_width=args.infer_width,
            person_padding=args.person_padding,
            score_threshold=args.sam_score_threshold,
            max_upscale=args.max_upscale,
        )
        active_ids = sorted(dict.fromkeys(active_ids))
        prune_missing_people(people, frame_index, args.max_missed_frames)

        elapsed = max(1e-6, time.perf_counter() - loop_start)
        instant_fps = 1.0 / elapsed
        smoothed_fps = instant_fps if smoothed_fps == 0 else (smoothed_fps * 0.85 + instant_fps * 0.15)

        main_frame = draw_main_frame(
            frame_bgr=frame_bgr,
            people=people,
            active_ids=active_ids,
            prompts=prompts,
            fps_text=f"Pipeline: {smoothed_fps:.1f} FPS | pessoas ativas: {len(active_ids)}",
        )
        side_panel = build_side_panel(
            active_ids=active_ids,
            people=people,
            panel_width=args.panel_width,
            panel_height=main_frame.shape[0],
            prompts=prompts,
            max_people=args.max_panel_people,
        )
        display = compose_display(main_frame, side_panel, args.display_width)

        if args.save_output_video:
            if output_writer is None:
                output_writer, output_path = create_video_writer(
                    output_path=args.output_video,
                    fps=source_fps,
                    frame_size=(display.shape[1], display.shape[0]),
                )
                print(f"Gravando video composto em: {output_path}")
            output_writer.write(display)

        cv2.imshow("YOLO + SAM3 PPE", display)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break

        frame_index += 1

    capture.release()
    if output_writer is not None:
        output_writer.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
