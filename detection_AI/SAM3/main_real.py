from __future__ import annotations

import argparse
import contextlib
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
SAM3_REPO_ROOT = PROJECT_ROOT / "sam3"
LOCAL_CHECKPOINT = SAM3_REPO_ROOT / "Arquivos" / "sam3.pt"
LOCAL_BPE = SAM3_REPO_ROOT / "sam3" / "assets" / "bpe_simple_vocab_16e6.txt.gz"

if SAM3_REPO_ROOT.exists():
    sys.path.insert(0, str(SAM3_REPO_ROOT))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Visualizacao em tempo quase real com SAM3."
    )
    parser.add_argument(
        "--source",
        default="0",
        help='Fonte de video: "0" para webcam ou caminho de arquivo.',
    )
    parser.add_argument(
        "--prompt",
        required=True,
        help='Prompts separados por virgula. Ex: "helmet,safety vest,gloves"',
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.2,
        help="Threshold de confianca do SAM3.",
    )
    parser.add_argument(
        "--process-every",
        type=int,
        default=12,
        help="Roda inferencia a cada N frames e reaproveita a ultima saida nos demais.",
    )
    parser.add_argument(
        "--infer-width",
        type=int,
        default=640,
        help="Largura usada na inferencia. Menor = mais fluido.",
    )
    parser.add_argument(
        "--display-width",
        type=int,
        default=960,
        help="Largura da janela de exibicao.",
    )
    parser.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cuda", "cpu"],
        help="Dispositivo para inferencia.",
    )
    parser.add_argument(
        "--clip-duration-sec",
        type=float,
        default=6.0,
        help="No modo arquivo, processa o video em blocos dessa duracao.",
    )
    parser.add_argument(
        "--sample-every",
        type=int,
        default=15,
        help="No modo arquivo, usa 1 frame a cada N frames.",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=40,
        help="Numero maximo de frames por bloco no modo arquivo.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs") / "real_preview",
        help="Pasta para overlays temporarios/resultado no modo arquivo.",
    )
    parser.add_argument(
        "--display-fps",
        type=float,
        default=0.0,
        help="Limita a exibicao para um FPS fixo. Ex: 1 para parecer webcam lenta.",
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
        import PIL  # noqa: F401
    except ModuleNotFoundError:
        missing.append("pillow")

    if missing:
        raise SystemExit(
            "Dependencias ausentes para o modo em tempo real:\n  pip install "
            + " ".join(missing)
            + "\n  pip install -e .\\sam3"
        )


def parse_prompts(prompt_text: str) -> list[str]:
    prompts = [part.strip() for part in prompt_text.replace(";", ",").split(",")]
    prompts = [prompt for prompt in prompts if prompt]
    if not prompts:
        raise SystemExit("Informe pelo menos um prompt em --prompt")
    return prompts


def color_for_label(label: str) -> tuple[int, int, int]:
    palette = [
        (255, 99, 71),
        (0, 200, 255),
        (124, 252, 0),
        (255, 215, 0),
        (255, 105, 180),
        (138, 43, 226),
        (255, 140, 0),
        (64, 224, 208),
    ]
    return palette[sum(ord(ch) for ch in label) % len(palette)]


def pick_device(device_arg: str) -> str:
    import torch

    if device_arg == "cuda":
        if not torch.cuda.is_available():
            raise SystemExit("CUDA foi solicitado, mas nao esta disponivel.")
        return "cuda"
    if device_arg == "cpu":
        return "cpu"
    return "cuda" if torch.cuda.is_available() else "cpu"


def build_model(device: str, threshold: float):
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


def infer_prompts(
    processor, frame_rgb: np.ndarray, prompts: list[str], infer_width: int
) -> list[dict]:
    import cv2
    from PIL import Image
    import torch

    orig_h, orig_w = frame_rgb.shape[:2]
    infer_width = max(64, min(infer_width, orig_w))
    infer_height = max(64, int(round(orig_h * (infer_width / orig_w))))
    infer_rgb = cv2.resize(
        frame_rgb, (infer_width, infer_height), interpolation=cv2.INTER_AREA
    )
    scale_x = orig_w / infer_width
    scale_y = orig_h / infer_height

    pil_image = Image.fromarray(infer_rgb)
    results = []
    autocast_device = "cuda" if torch.cuda.is_available() else "cpu"
    cuda_autocast_guard = (
        torch.cuda.amp.autocast(enabled=False)
        if torch.cuda.is_available()
        else contextlib.nullcontext()
    )
    with torch.autocast(device_type=autocast_device, enabled=False), cuda_autocast_guard:
        for prompt in prompts:
            state = processor.set_image(pil_image)
            output = processor.set_text_prompt(prompt=prompt, state=state)
            masks_small = output["masks"].detach().cpu().numpy()
            boxes = output["boxes"].detach().cpu().numpy()
            scores = output["scores"].detach().cpu().numpy()

            masks = []
            for mask in masks_small:
                if mask.ndim == 3:
                    mask_2d = mask.squeeze(0)
                else:
                    mask_2d = mask
                resized_mask = cv2.resize(
                    mask_2d.astype(np.uint8),
                    (orig_w, orig_h),
                    interpolation=cv2.INTER_NEAREST,
                ).astype(bool)
                masks.append(resized_mask)
            masks = np.asarray(masks)

            if len(boxes) > 0:
                boxes = boxes.astype(np.float32)
                boxes[:, [0, 2]] *= scale_x
                boxes[:, [1, 3]] *= scale_y
            results.append(
                {
                    "prompt": prompt,
                    "masks": masks,
                    "boxes": boxes,
                    "scores": scores,
                }
            )
    return results


def draw_results(frame_bgr: np.ndarray, results: list[dict], fps_text: str) -> np.ndarray:
    import cv2

    canvas = frame_bgr.copy()
    summary_lines = []
    for result in results:
        prompt = result["prompt"]
        color = color_for_label(prompt)
        masks = result["masks"]
        boxes = result["boxes"]
        scores = result["scores"]
        summary_lines.append(f"{prompt}: {len(scores)}")

        for idx in range(len(scores)):
            mask = masks[idx]
            if mask.ndim == 3:
                mask = mask.squeeze(0)
            mask = mask.astype(bool)
            if mask.any():
                overlay_color = np.array(color, dtype=np.uint8)
                canvas[mask] = (
                    canvas[mask].astype(np.float32) * 0.45
                    + overlay_color.astype(np.float32) * 0.55
                ).astype(np.uint8)
                ys, xs = np.where(mask)
                x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
            else:
                x0, y0, x1, y1 = [int(round(v)) for v in boxes[idx]]

            cv2.rectangle(canvas, (x0, y0), (x1, y1), color, 2)
            label = f"{prompt} {scores[idx]:.2f}"
            cv2.putText(
                canvas,
                label,
                (x0, max(18, y0 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
                cv2.LINE_AA,
            )

    cv2.rectangle(canvas, (10, 10), (340, 70), (20, 20, 20), -1)
    cv2.putText(
        canvas,
        fps_text,
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        canvas,
        "Q para sair",
        (20, 62),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (220, 220, 220),
        1,
        cv2.LINE_AA,
    )
    if summary_lines:
        panel_height = 28 + 24 * len(summary_lines)
        cv2.rectangle(canvas, (10, 84), (320, 84 + panel_height), (20, 20, 20), -1)
        for idx, line in enumerate(summary_lines):
            cv2.putText(
                canvas,
                line,
                (20, 108 + idx * 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
    return canvas


def open_capture(source_text: str):
    import cv2

    source = int(source_text) if source_text.isdigit() else source_text
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise SystemExit(f"Nao foi possivel abrir a fonte de video: {source_text}")
    return cap


def resize_for_display(frame: np.ndarray, display_width: int) -> np.ndarray:
    import cv2

    if display_width <= 0 or frame.shape[1] == display_width:
        return frame
    scale = display_width / frame.shape[1]
    display_height = max(1, int(round(frame.shape[0] * scale)))
    return cv2.resize(
        frame,
        (display_width, display_height),
        interpolation=cv2.INTER_AREA,
    )


def throttle_display(display_fps: float, last_display_time: float | None) -> float:
    if display_fps <= 0:
        return time.perf_counter()
    now = time.perf_counter()
    min_interval = 1.0 / display_fps
    if last_display_time is not None:
        elapsed = now - last_display_time
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
    return time.perf_counter()


def is_video_file_source(source_text: str) -> bool:
    path = Path(source_text)
    return path.exists() and path.suffix.lower() in {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def run_video_file_with_predictor(args, prompts: list[str]) -> None:
    import cv2
    from main import prepare_video_frames, save_video_frame_outputs, _sanitize_prompt_for_path
    from sam3.model_builder import build_sam3_video_predictor

    if not LOCAL_BPE.exists():
        raise SystemExit(f"Arquivo BPE nao encontrado: {LOCAL_BPE}")
    if not LOCAL_CHECKPOINT.exists():
        raise SystemExit(f"Checkpoint local nao encontrado: {LOCAL_CHECKPOINT}")

    video_path = Path(args.source).expanduser().resolve()
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise SystemExit(f"Nao foi possivel abrir o video: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.release()
    fps = fps if fps and fps > 0 else 30.0
    total_duration_sec = total_frames / fps if total_frames > 0 else args.clip_duration_sec

    output_dir = (
        args.output_dir.expanduser().resolve()
        / _sanitize_prompt_for_path("_".join(prompts))
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    predictor = build_sam3_video_predictor(
        checkpoint_path=str(LOCAL_CHECKPOINT),
        bpe_path=str(LOCAL_BPE),
    )
    last_display_time = None

    clip_start_sec = 0.0
    global_frame_offset = 0
    while clip_start_sec < total_duration_sec:
        prepared_resource = prepare_video_frames(
            video_path=video_path,
            output_root=PROJECT_ROOT / "prepared_videos" / "real_preview_chunks",
            clip_start_sec=clip_start_sec,
            clip_duration_sec=args.clip_duration_sec,
            sample_every=args.sample_every,
            max_frames=args.max_frames,
        )
        frame_count_in_chunk = len(
            [
                p
                for p in prepared_resource.iterdir()
                if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
            ]
        )
        if frame_count_in_chunk == 0:
            break

        for prompt in prompts:
            session_response = predictor.handle_request(
                request={
                    "type": "start_session",
                    "resource_path": str(prepared_resource),
                    "offload_video_to_cpu": True,
                }
            )
            session_id = session_response["session_id"]

            prompt_response = predictor.handle_request(
                request={
                    "type": "add_prompt",
                    "session_id": session_id,
                    "frame_index": 0,
                    "text": prompt,
                }
            )

            first_index = global_frame_offset + prompt_response["frame_index"]
            save_video_frame_outputs(
                frames_dir=prepared_resource,
                output_dir=output_dir,
                frame_index=prompt_response["frame_index"],
                output_frame_index=first_index,
                outputs=prompt_response["outputs"],
                prompt_label=prompt,
            )

            overlay_path = output_dir / "frames" / f"frame_{first_index:04d}_overlay.jpg"
            overlay = cv2.imread(str(overlay_path))
            if overlay is not None:
                overlay = resize_for_display(overlay, args.display_width)
                last_display_time = throttle_display(args.display_fps, last_display_time)
                cv2.imshow("SAM3 Real-Time", overlay)
                if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                    predictor.handle_request(
                        request={"type": "close_session", "session_id": session_id}
                    )
                    cv2.destroyAllWindows()
                    return

            for item in predictor.handle_stream_request(
                request={
                    "type": "propagate_in_video",
                    "session_id": session_id,
                    "start_frame_index": 0,
                    "propagation_direction": "forward",
                    "max_frame_num_to_track": frame_count_in_chunk,
                }
            ):
                output_index = global_frame_offset + item["frame_index"]
                save_video_frame_outputs(
                    frames_dir=prepared_resource,
                    output_dir=output_dir,
                    frame_index=item["frame_index"],
                    output_frame_index=output_index,
                    outputs=item["outputs"],
                    prompt_label=prompt,
                )
                overlay_path = output_dir / "frames" / f"frame_{output_index:04d}_overlay.jpg"
                overlay = cv2.imread(str(overlay_path))
                if overlay is not None:
                    overlay = resize_for_display(overlay, args.display_width)
                    last_display_time = throttle_display(args.display_fps, last_display_time)
                    cv2.imshow("SAM3 Real-Time", overlay)
                    if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                        predictor.handle_request(
                            request={"type": "close_session", "session_id": session_id}
                        )
                        cv2.destroyAllWindows()
                        return

            predictor.handle_request(
                request={"type": "close_session", "session_id": session_id}
            )

        global_frame_offset += frame_count_in_chunk
        clip_start_sec += args.clip_duration_sec

    cv2.destroyAllWindows()


def main() -> None:
    ensure_dependencies()
    parser = build_parser()
    args = parser.parse_args()

    import cv2

    prompts = parse_prompts(args.prompt)
    device = pick_device(args.device)

    print(f"Usando device: {device}")
    print(f"Prompts ativos: {', '.join(prompts)}")

    if is_video_file_source(args.source):
        run_video_file_with_predictor(args, prompts)
        return

    processor = build_model(device=device, threshold=args.threshold)
    capture = open_capture(args.source)

    frame_index = 0
    last_results: list[dict] = []
    smoothed_fps = 0.0
    last_display_time = None

    while True:
        ok, frame_bgr = capture.read()
        if not ok:
            break

        inference_start = time.perf_counter()
        if frame_index % max(1, args.process_every) == 0:
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            last_results = infer_prompts(
                processor, frame_rgb, prompts, infer_width=args.infer_width
            )
        elapsed = time.perf_counter() - inference_start
        instant_fps = (
            1.0 / elapsed if elapsed > 0 and frame_index % max(1, args.process_every) == 0 else smoothed_fps
        )
        smoothed_fps = instant_fps if smoothed_fps == 0 else (smoothed_fps * 0.85 + instant_fps * 0.15)

        annotated = draw_results(
            frame_bgr,
            last_results,
            fps_text=(
                f"Inferencia aprox: {smoothed_fps:.1f} FPS | "
                f"skip={args.process_every} | infer={args.infer_width}px"
            ),
        )

        annotated = resize_for_display(annotated, args.display_width)

        last_display_time = throttle_display(args.display_fps, last_display_time)
        cv2.imshow("SAM3 Real-Time", annotated)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        frame_index += 1

    capture.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
