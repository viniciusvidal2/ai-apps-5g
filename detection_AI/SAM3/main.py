from __future__ import annotations

import argparse
import sys
from pathlib import Path

import shutil
import json

PROJECT_ROOT = Path(__file__).resolve().parent
SAM3_REPO_ROOT = PROJECT_ROOT / "sam3"
LOCAL_CHECKPOINT = SAM3_REPO_ROOT / "Arquivos" / "sam3.pt"
LOCAL_BPE = SAM3_REPO_ROOT / "sam3" / "assets" / "bpe_simple_vocab_16e6.txt.gz"

# Garante que o import `sam3` aponte para o pacote Python dentro do repo clonado.
if SAM3_REPO_ROOT.exists():
    sys.path.insert(0, str(SAM3_REPO_ROOT))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Exemplo simples para usar o SAM3 localmente."
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    image_parser = subparsers.add_parser("image", help="Segmenta uma imagem por texto.")
    image_parser.add_argument("--input", type=Path, required=True, help="Caminho da imagem.")
    image_parser.add_argument("--prompt", required=True, help="Texto a procurar na imagem.")
    image_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Pasta onde as mascaras serao salvas.",
    )
    image_parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Threshold de confianca do SAM3.",
    )

    video_parser = subparsers.add_parser("video", help="Segmenta/rastreia um conceito em video.")
    video_parser.add_argument("--input", type=Path, required=True, help="Caminho do video.")
    video_parser.add_argument(
        "--prompt", required=True, help="Texto do objeto/conceito para rastrear."
    )
    video_parser.add_argument(
        "--frame-index",
        type=int,
        default=0,
        help="Frame inicial para adicionar o prompt.",
    )
    video_parser.add_argument(
        "--clip-start-sec",
        type=float,
        default=0.0,
        help="Segundo inicial do recorte do video.",
    )
    video_parser.add_argument(
        "--clip-duration-sec",
        type=float,
        default=12.0,
        help="Duracao maxima do recorte em segundos.",
    )
    video_parser.add_argument(
        "--sample-every",
        type=int,
        default=10,
        help="Salva 1 frame a cada N frames do video original.",
    )
    video_parser.add_argument(
        "--max-frames",
        type=int,
        default=90,
        help="Numero maximo de frames a extrair para o SAM3.",
    )
    video_parser.add_argument(
        "--prepared-dir",
        type=Path,
        default=Path("prepared_videos"),
        help="Pasta base para salvar frames extraidos.",
    )
    video_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs") / "video",
        help="Pasta base para salvar overlays e mascaras do video.",
    )
    video_parser.add_argument(
        "--no-propagation",
        action="store_true",
        help="Salva apenas o frame do prompt, sem propagar para os demais frames.",
    )
    video_parser.add_argument(
        "--process-full-video",
        action="store_true",
        help="Processa o video inteiro em blocos menores e depois junta a saida.",
    )
    return parser


def ensure_runtime_dependencies() -> None:
    try:
        import torch  # noqa: F401
        import huggingface_hub  # noqa: F401
        import PIL  # noqa: F401
    except ModuleNotFoundError as exc:
        missing = exc.name or "dependencia desconhecida"
        raise SystemExit(
            "Ambiente incompleto para rodar o SAM3.\n"
            f"Modulo ausente: {missing}\n\n"
            "Instale assim dentro da pasta do projeto:\n"
            "  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128\n"
            "  pip install -e .\\sam3\n"
            "  pip install pillow\n\n"
            "Depois faca login no Hugging Face:\n"
            "  hf auth login\n"
        ) from exc


def prepare_video_frames(
    video_path: Path,
    output_root: Path,
    clip_start_sec: float,
    clip_duration_sec: float,
    sample_every: int,
    max_frames: int,
) -> Path:
    try:
        import cv2
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Para cortar o video e amostrar frames, instale OpenCV no ambiente atual:\n"
            "  pip install opencv-python"
        ) from exc

    if sample_every < 1:
        raise SystemExit("--sample-every precisa ser >= 1")
    if max_frames < 1:
        raise SystemExit("--max-frames precisa ser >= 1")
    if clip_start_sec < 0:
        raise SystemExit("--clip-start-sec nao pode ser negativo")
    if clip_duration_sec <= 0:
        raise SystemExit("--clip-duration-sec precisa ser > 0")

    output_dir = (
        output_root.expanduser().resolve()
        / f"{video_path.stem}_start{clip_start_sec:g}_dur{clip_duration_sec:g}_step{sample_every}"
    )
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise SystemExit(f"Nao foi possivel abrir o video: {video_path}")

    fps = capture.get(cv2.CAP_PROP_FPS)
    fps = fps if fps and fps > 0 else 30.0
    start_frame = max(0, int(round(clip_start_sec * fps)))
    end_frame = int(round((clip_start_sec + clip_duration_sec) * fps))

    capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    saved_count = 0
    current_frame = start_frame
    print(
        "Preparando video para economizar memoria: "
        f"inicio={clip_start_sec}s duracao={clip_duration_sec}s "
        f"amostragem=1/{sample_every} max_frames={max_frames}"
    )

    while current_frame < end_frame and saved_count < max_frames:
        ok, frame = capture.read()
        if not ok:
            break

        relative_index = current_frame - start_frame
        if relative_index % sample_every == 0:
            frame_path = output_dir / f"{saved_count}.jpg"
            if not cv2.imwrite(str(frame_path), frame):
                capture.release()
                raise SystemExit(f"Falha ao salvar frame em: {frame_path}")
            saved_count += 1

        current_frame += 1

    capture.release()

    if saved_count == 0:
        raise SystemExit(
            "Nenhum frame foi extraido. Tente diminuir --clip-start-sec ou --sample-every."
        )

    print(f"Frames preparados: {saved_count}")
    print(f"Pasta de frames: {output_dir}")
    return output_dir


def _find_prepared_frame_path(frames_dir: Path, frame_index: int) -> Path:
    for suffix in (".jpg", ".jpeg", ".png", ".bmp", ".webp"):
        candidate = frames_dir / f"{frame_index}{suffix}"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"Nao encontrei o frame {frame_index} na pasta preparada: {frames_dir}"
    )


def _color_for_obj(obj_id: int) -> tuple[int, int, int]:
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
    return palette[obj_id % len(palette)]


def _color_for_label(label: str, obj_id: int) -> tuple[int, int, int]:
    palette = [
        (255, 99, 71),
        (0, 200, 255),
        (124, 252, 0),
        (255, 215, 0),
        (255, 105, 180),
        (138, 43, 226),
        (255, 140, 0),
        (64, 224, 208),
        (220, 20, 60),
        (50, 205, 50),
    ]
    return palette[(sum(ord(ch) for ch in label) + obj_id) % len(palette)]


def _parse_prompts(prompt_text: str) -> list[str]:
    prompts = [part.strip() for part in prompt_text.replace(";", ",").split(",")]
    prompts = [prompt for prompt in prompts if prompt]
    if not prompts:
        raise SystemExit("Informe pelo menos um prompt em --prompt")
    return prompts


def save_video_frame_outputs(
    frames_dir: Path,
    output_dir: Path,
    frame_index: int,
    outputs: dict,
    output_frame_index: int | None = None,
    prompt_label: str | None = None,
) -> None:
    import numpy as np
    from PIL import Image, ImageDraw

    frame_path = _find_prepared_frame_path(frames_dir, frame_index)
    out_obj_ids = outputs.get("out_obj_ids", [])
    out_boxes_xywh = outputs.get("out_boxes_xywh", [])
    out_binary_masks = outputs.get("out_binary_masks", [])
    out_probs = outputs.get("out_probs", [])

    output_frame_index = frame_index if output_frame_index is None else output_frame_index

    frame_output_dir = output_dir / "frames"
    masks_output_dir = output_dir / "masks"
    frame_output_dir.mkdir(parents=True, exist_ok=True)
    masks_output_dir.mkdir(parents=True, exist_ok=True)
    overlay_path = frame_output_dir / f"frame_{output_frame_index:04d}_overlay.jpg"
    metadata_path = frame_output_dir / f"frame_{output_frame_index:04d}.json"

    if overlay_path.exists():
        overlay_image = Image.open(overlay_path).convert("RGB")
        overlay_np = np.array(overlay_image, dtype=np.uint8)
        frame_image = overlay_image.copy()
    else:
        frame_image = Image.open(frame_path).convert("RGB")
        overlay_np = np.array(frame_image, dtype=np.uint8)

    if metadata_path.exists():
        with metadata_path.open("r", encoding="utf-8") as f:
            metadata = json.load(f)
    else:
        metadata = {
            "frame_index": output_frame_index,
            "source_frame_index": frame_index,
            "frame_path": str(frame_path),
            "objects": [],
        }

    prompt_slug = _sanitize_prompt_for_path(prompt_label or "prompt")

    for idx, obj_id in enumerate(out_obj_ids):
        obj_id = int(obj_id)
        color_tuple = _color_for_label(prompt_label or "prompt", obj_id)
        color = np.array(color_tuple, dtype=np.uint8)
        mask = np.asarray(out_binary_masks[idx]).astype(bool)
        if mask.ndim == 3:
            mask = mask.squeeze(0)

        if mask.any():
            overlay_np[mask] = (
                overlay_np[mask].astype(np.float32) * 0.45 + color.astype(np.float32) * 0.55
            ).astype(np.uint8)

        mask_path = (
            masks_output_dir
            / f"frame_{output_frame_index:04d}_{prompt_slug}_obj_{obj_id}.png"
        )
        Image.fromarray((mask.astype(np.uint8) * 255), mode="L").save(mask_path)

        box = None
        if mask.any():
            ys, xs = np.where(mask)
            x0 = int(xs.min())
            y0 = int(ys.min())
            x1 = int(xs.max())
            y1 = int(ys.max())
            box = [x0, y0, x1, y1]
        elif idx < len(out_boxes_xywh):
            box_values = [float(v) for v in out_boxes_xywh[idx]]
            w, h = frame_image.size
            cx, cy, bw, bh = box_values
            x0 = max(0.0, min(w - 1.0, (cx - bw / 2.0) * w))
            y0 = max(0.0, min(h - 1.0, (cy - bh / 2.0) * h))
            x1 = max(0.0, min(w - 1.0, (cx + bw / 2.0) * w))
            y1 = max(0.0, min(h - 1.0, (cy + bh / 2.0) * h))
            box = [x0, y0, x1, y1]

        metadata["objects"].append(
            {
                "prompt": prompt_label,
                "obj_id": obj_id,
                "score": float(out_probs[idx]) if idx < len(out_probs) else None,
                "box_xyxy": box,
                "mask_path": str(mask_path),
            }
        )

    overlay_image = Image.fromarray(overlay_np, mode="RGB")
    draw = ImageDraw.Draw(overlay_image)
    for obj in metadata["objects"]:
        if obj["box_xyxy"] is not None:
            x0, y0, x1, y1 = obj["box_xyxy"]
            color = _color_for_label(obj.get("prompt") or "prompt", obj["obj_id"])
            draw.rectangle((x0, y0, x1, y1), outline=color, width=3)
            score_text = (
                f"{obj.get('prompt') or 'prompt'} id={obj['obj_id']} score={obj['score']:.3f}"
                if obj["score"] is not None
                else f"{obj.get('prompt') or 'prompt'} id={obj['obj_id']}"
            )
            draw.text((x0 + 4, max(0, y0 - 18)), score_text, fill=color)

    overlay_image.save(overlay_path, quality=95)
    with metadata_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def recreate_video_from_frames(
    prepared_frames_dir: Path,
    output_dir: Path,
    sample_every: int,
    original_fps: float = 30.0,
) -> Path:
    try:
        import cv2
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Para recriar o video, instale OpenCV no ambiente atual:\n"
            "  pip install opencv-python"
        ) from exc

    overlay_dir = output_dir / "frames"
    overlay_map = {}
    if overlay_dir.exists():
        for path in overlay_dir.glob("frame_*_overlay.jpg"):
            try:
                frame_index = int(path.stem.replace("frame_", "").replace("_overlay", ""))
            except ValueError:
                continue
            overlay_map[frame_index] = path

    prepared_map = {}
    if prepared_frames_dir.exists():
        for path in prepared_frames_dir.iterdir():
            if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
                try:
                    prepared_map[int(path.stem)] = path
                except ValueError:
                    continue

    frame_indices = sorted(set(overlay_map.keys()) | set(prepared_map.keys()))
    if not frame_indices:
        raise SystemExit(f"Nenhum frame encontrado para recriar o video em: {output_dir}")

    first_source = overlay_map.get(frame_indices[0], prepared_map.get(frame_indices[0]))
    first_image = cv2.imread(str(first_source))
    if first_image is None:
        raise SystemExit(f"Nao foi possivel abrir o frame: {first_source}")

    height, width = first_image.shape[:2]
    out_fps = max(1.0, original_fps / max(1, sample_every))
    video_path = output_dir / "segmentation_overlay.mp4"
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        out_fps,
        (width, height),
    )
    if not writer.isOpened():
        raise SystemExit(f"Nao foi possivel criar o video: {video_path}")

    for frame_index in frame_indices:
        source_path = overlay_map.get(frame_index, prepared_map.get(frame_index))
        frame = cv2.imread(str(source_path))
        if frame is None:
            writer.release()
            raise SystemExit(f"Nao foi possivel abrir o frame: {source_path}")
        if frame.shape[:2] != (height, width):
            frame = cv2.resize(frame, (width, height))
        writer.write(frame)

    writer.release()
    return video_path


def _sanitize_prompt_for_path(prompt: str) -> str:
    safe = prompt.strip().replace(" ", "_")
    return safe or "prompt"


def process_video_chunk(
    predictor,
    prepared_resource: Path,
    output_dir: Path,
    prompt: str,
    prompt_frame_index: int,
    max_frames: int,
    no_propagation: bool,
    global_frame_offset: int = 0,
) -> int:
    session_response = predictor.handle_request(
        request={
            "type": "start_session",
            "resource_path": str(prepared_resource),
            "offload_video_to_cpu": True,
        }
    )
    session_id = session_response["session_id"]
    print(f"Sessao iniciada: {session_id}")

    prompt_response = predictor.handle_request(
        request={
            "type": "add_prompt",
            "session_id": session_id,
            "frame_index": prompt_frame_index,
            "text": prompt,
        }
    )

    outputs = prompt_response["outputs"]
    print("Prompt enviado com sucesso.")
    print(f"Chaves retornadas: {list(outputs.keys())}")
    initial_output_index = global_frame_offset + prompt_response["frame_index"]
    save_video_frame_outputs(
        frames_dir=prepared_resource,
        output_dir=output_dir,
        frame_index=prompt_response["frame_index"],
        output_frame_index=initial_output_index,
        outputs=outputs,
        prompt_label=prompt,
    )
    saved_count = 1

    if not no_propagation:
        print("Propagando segmentacao pelos frames preparados...")
        for item in predictor.handle_stream_request(
            request={
                "type": "propagate_in_video",
                "session_id": session_id,
                "start_frame_index": prompt_frame_index,
                "propagation_direction": "forward",
                "max_frame_num_to_track": max_frames,
            }
        ):
            save_video_frame_outputs(
                frames_dir=prepared_resource,
                output_dir=output_dir,
                frame_index=item["frame_index"],
                output_frame_index=global_frame_offset + item["frame_index"],
                outputs=item["outputs"],
                prompt_label=prompt,
            )
            saved_count += 1
        print(f"Frames salvos com segmentacao: {saved_count}")

    predictor.handle_request(
        request={
            "type": "close_session",
            "session_id": session_id,
        }
    )
    return saved_count


def run_image(args: argparse.Namespace) -> None:
    import numpy as np
    import torch
    from PIL import Image
    from sam3.model_builder import build_sam3_image_model
    from sam3.model.sam3_image_processor import Sam3Processor

    image_path = args.input.expanduser().resolve()
    if not image_path.exists():
        raise SystemExit(f"Imagem nao encontrada: {image_path}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Usando device: {device}")
    print("Carregando modelo SAM3. O primeiro download pode demorar...")

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
    processor = Sam3Processor(
        model=model, device=device, confidence_threshold=args.threshold
    )

    image = Image.open(image_path).convert("RGB")
    state = processor.set_image(image)
    output = processor.set_text_prompt(prompt=args.prompt, state=state)

    masks = output["masks"].detach().cpu()
    boxes = output["boxes"].detach().cpu()
    scores = output["scores"].detach().cpu()

    print(f"Objetos encontrados: {len(scores)}")
    for index, (box, score) in enumerate(zip(boxes, scores), start=1):
        x0, y0, x1, y1 = [round(value.item(), 2) for value in box]
        print(
            f"[{index}] score={score.item():.4f} "
            f"box=({x0}, {y0}, {x1}, {y1})"
        )

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    for index, mask in enumerate(masks, start=1):
        mask_image = (mask.squeeze(0).numpy().astype(np.uint8)) * 255
        mask_path = output_dir / f"{image_path.stem}_mask_{index}.png"
        Image.fromarray(mask_image, mode="L").save(mask_path)
        print(f"Mask salva em: {mask_path}")


def run_video(args: argparse.Namespace) -> None:
    import torch
    import cv2
    from sam3.model_builder import build_sam3_video_predictor

    if not torch.cuda.is_available():
        raise SystemExit(
            "O modo video do exemplo precisa de CUDA/GPU, porque o predictor usa .cuda()."
        )

    video_path = args.input.expanduser().resolve()
    if not video_path.exists():
        raise SystemExit(f"Video nao encontrado: {video_path}")
    if not LOCAL_BPE.exists():
        raise SystemExit(f"Arquivo BPE nao encontrado: {LOCAL_BPE}")
    if not LOCAL_CHECKPOINT.exists():
        raise SystemExit(f"Checkpoint local nao encontrado: {LOCAL_CHECKPOINT}")
    prompts = _parse_prompts(args.prompt)

    capture = cv2.VideoCapture(str(video_path))
    fps = capture.get(cv2.CAP_PROP_FPS)
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    capture.release()
    fps = fps if fps and fps > 0 else 30.0
    output_dir = (
        args.output_dir.expanduser().resolve()
        / _sanitize_prompt_for_path("_".join(prompts))
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Carregando video predictor SAM3...")
    predictor = build_sam3_video_predictor(
        checkpoint_path=str(LOCAL_CHECKPOINT),
        bpe_path=str(LOCAL_BPE),
    )

    if args.process_full_video:
        total_duration_sec = total_frames / fps if total_frames > 0 else args.clip_duration_sec
        chunk_duration_sec = args.clip_duration_sec
        chunk_index = 0
        global_frame_offset = 0
        clip_start_sec = 0.0
        while clip_start_sec < total_duration_sec:
            print(
                f"Processando bloco {chunk_index + 1} "
                f"(inicio={clip_start_sec:.2f}s duracao={chunk_duration_sec:.2f}s)"
            )
            prepared_resource = prepare_video_frames(
                video_path=video_path,
                output_root=args.prepared_dir / "chunks",
                clip_start_sec=clip_start_sec,
                clip_duration_sec=chunk_duration_sec,
                sample_every=args.sample_every,
                max_frames=args.max_frames,
            )
            for prompt in prompts:
                print(f"Detectando prompt no bloco atual: {prompt}")
                process_video_chunk(
                    predictor=predictor,
                    prepared_resource=prepared_resource,
                    output_dir=output_dir,
                    prompt=prompt,
                    prompt_frame_index=0,
                    max_frames=args.max_frames,
                    no_propagation=args.no_propagation,
                    global_frame_offset=global_frame_offset,
                )
            chunk_frame_count = len(
                [
                    p
                    for p in prepared_resource.iterdir()
                    if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
                ]
            )
            global_frame_offset += chunk_frame_count
            clip_start_sec += chunk_duration_sec
            chunk_index += 1

        recreated_video_path = recreate_video_from_frames(
            prepared_frames_dir=output_dir / "frames",
            output_dir=output_dir,
            sample_every=args.sample_every,
            original_fps=fps,
        )
        print(f"Video completo recriado em: {recreated_video_path}")
    else:
        prepared_resource = prepare_video_frames(
            video_path=video_path,
            output_root=args.prepared_dir,
            clip_start_sec=args.clip_start_sec,
            clip_duration_sec=args.clip_duration_sec,
            sample_every=args.sample_every,
            max_frames=args.max_frames,
        )
        for prompt in prompts:
            print(f"Detectando prompt: {prompt}")
            process_video_chunk(
                predictor=predictor,
                prepared_resource=prepared_resource,
                output_dir=output_dir,
                prompt=prompt,
                prompt_frame_index=args.frame_index,
                max_frames=args.max_frames,
                no_propagation=args.no_propagation,
                global_frame_offset=0,
            )
        recreated_video_path = recreate_video_from_frames(
            prepared_frames_dir=prepared_resource,
            output_dir=output_dir,
            sample_every=args.sample_every,
            original_fps=fps,
        )
        print(f"Video recriado em: {recreated_video_path}")


def main() -> None:
    ensure_runtime_dependencies()
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.mode == "image":
            run_image(args)
        elif args.mode == "video":
            run_video(args)
        else:
            raise SystemExit(f"Modo invalido: {args.mode}")
    except Exception as exc:
        message = str(exc)
        if "401" in message or "403" in message or "huggingface" in message.lower():
            raise SystemExit(
                f"{message}\n\n"
                "Se o erro for de permissao, confirme:\n"
                "1. Seu acesso ao repo facebook/sam3 foi aprovado.\n"
                "2. Voce executou: hf auth login\n"
            ) from exc
        raise


if __name__ == "__main__":
    main()
