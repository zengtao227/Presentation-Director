"""
generate_images.py — AI image generation / prompt export for Presentation Director.

AUTOMATIC backends (no human involvement):
  --api stub        Solid-color PNG for testing, no API key needed
  --api hf          Hugging Face FLUX.1-schnell, free with HF_TOKEN
                    (free account at huggingface.co, token from Settings → Access Tokens)
  --api dall-e-3    OpenAI DALL-E 3  (OPENAI_API_KEY, ~$0.04/image)
  --api flux        fal.ai Flux      (FAL_KEY, ~$0.003/image)

MANUAL workflow — best zero-cost option:
  show               Print concise prompts to stdout for chat handoff.
  --api prompt-only  Export the same concise prompts to image-prompts.md.
                     Paste into any tool, then run `place` to register it.

REGISTER manually downloaded images:
  place              Scan assets/images/ for plan targets and record them.
  place --source ~/Downloads/cover.png --target-id cover-background
                     Copy one arbitrary source image to the planned output path.
  place --sources '{"cover-background":"~/Downloads/cover.png"}'
                     Copy and record multiple arbitrary source images.

Free online tools that accept these prompts (no API key needed):
  • Microsoft Copilot / Bing Image Creator  →  copilot.microsoft.com  (DALL-E 3, generous free)
  • Google ImageFX                          →  aitestkitchen.withgoogle.com/tools/image-fx
  • Adobe Firefly                           →  firefly.adobe.com  (25 free credits/month)
  • Ideogram                                →  ideogram.ai  (free tier, good quality)
  • Leonardo.ai                             →  leonardo.ai  (free daily credits)

Usage:
  python3 generate_images.py --task-dir PPTX/<slug> --api stub
  python3 generate_images.py --task-dir PPTX/<slug> --api hf
  python3 generate_images.py --task-dir PPTX/<slug> show
  python3 generate_images.py --task-dir PPTX/<slug> --api prompt-only
  python3 generate_images.py --task-dir PPTX/<slug> place
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import struct
import subprocess
import sys
import time
import urllib.request
import zlib
from pathlib import Path

MAX_ATTEMPTS: int = 3
STUB_COLORS: dict[str, tuple[int, int, int]] = {
    "cover": (10, 25, 60),
    "section-divider": (20, 40, 80),
    "global-theme": (15, 30, 70),
    "content": (240, 240, 245),
    "end": (5, 15, 40),
}
DEFAULT_STUB_COLOR: tuple[int, int, int] = (30, 50, 90)
IMAGE_EXTENSIONS: set[str] = {".png", ".jpg", ".jpeg", ".webp"}
NEGATIVE_PROMPT: str = (
    "text, letters, numbers, words, watermark, logo, brand, people, person, "
    "face, hand, body, border, frame, UI, interface, button, nsfw"
)


# ---------------------------------------------------------------------------
# Minimal PNG writer (no Pillow needed)
# ---------------------------------------------------------------------------

def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


def write_solid_png(path: Path, width: int, height: int, rgb: tuple[int, int, int]) -> None:
    r, g, b = rgb
    path.parent.mkdir(parents=True, exist_ok=True)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    row = bytes([0] + [r, g, b] * width)
    idat = zlib.compress(b"".join(row for _ in range(height)))
    with path.open("wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(_png_chunk(b"IHDR", ihdr))
        f.write(_png_chunk(b"IDAT", idat))
        f.write(_png_chunk(b"IEND", b""))


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _base_prompt(target: dict) -> str:
    return str(target.get("prompt_draft", "Abstract textured background, minimal, no text, no people"))


def read_pre_v1_targets(task_dir: Path) -> list[dict]:
    plan_path: Path = task_dir / "image-plan.json"
    if not plan_path.exists():
        print(f"No image-plan.json at {plan_path}.")
        return []

    with plan_path.open(encoding="utf-8") as f:
        plan: dict = json.load(f)

    return [
        target for target in plan.get("targets", [])
        if isinstance(target, dict) and str(target.get("phase", "pre-v1")) == "pre-v1"
    ]


def target_id(target: dict) -> str:
    return str(target.get("id", "unknown"))


def is_relative_to_path(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def image_output_root(task_dir: Path) -> Path:
    return task_dir / "assets" / "images"


def resolve_image_output_path(task_dir: Path, raw_path: str) -> Path:
    path: Path = Path(raw_path).expanduser()
    candidate: Path = path if path.is_absolute() else task_dir / path
    image_root: Path = image_output_root(task_dir).resolve()
    resolved: Path = candidate.resolve(strict=False)
    if not is_relative_to_path(resolved, image_root):
        raise ValueError(f"image output_path must stay under {image_root}: {raw_path}")
    if resolved.suffix.lower() not in IMAGE_EXTENSIONS:
        raise ValueError(f"image output_path must use an image extension: {raw_path}")
    return resolved


def target_output_path(task_dir: Path, target: dict) -> Path:
    target_name: str = target_id(target)
    raw_path: str = str(target.get("output_path", f"assets/images/{target_name}.png"))
    return resolve_image_output_path(task_dir, raw_path)


def target_by_id(targets: list[dict], requested_target_id: str) -> dict | None:
    for target in targets:
        if target_id(target) == requested_target_id:
            return target
    return None


# ---------------------------------------------------------------------------
# Automatic backends
# ---------------------------------------------------------------------------

def generate_stub(target: dict, out_path: Path) -> None:
    color = STUB_COLORS.get(str(target.get("slide_role", "")), DEFAULT_STUB_COLOR)
    write_solid_png(out_path, 1920, 1080, color)


def generate_hf(prompt: str, out_path: Path) -> None:
    """Hugging Face Inference API — free with a free HF account token."""
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        raise RuntimeError(
            "HF_TOKEN not set.\n"
            "  1. Create a free account at https://huggingface.co\n"
            "  2. Go to Settings → Access Tokens → New Token (read scope)\n"
            "  3. Run: export HF_TOKEN=hf_your_token_here\n"
            "  Or use --api prompt-only for a zero-account option."
        )
    url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    payload = json.dumps({"inputs": prompt}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req, timeout=120) as resp:
        ct = resp.headers.get("Content-Type", "")
        data = resp.read()
    if "image" not in ct:
        raise RuntimeError(f"HF did not return an image (Content-Type: {ct}). Response: {data[:200]}")
    with out_path.open("wb") as f:
        f.write(data)


def generate_dalle3(prompt: str, out_path: Path) -> None:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not set. "
            "Use --api hf (free with HF account) or --api prompt-only (no account needed)."
        )
    try:
        import openai  # type: ignore
    except ImportError:
        raise RuntimeError("openai not installed. Run: pip install openai")
    client = openai.OpenAI(api_key=api_key)
    response = client.images.generate(model="dall-e-3", prompt=prompt, size="1792x1024", n=1)
    url: str = response.data[0].url
    out_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, out_path)


def generate_flux_fal(prompt: str, out_path: Path) -> None:
    api_key = os.environ.get("FAL_KEY", "")
    if not api_key:
        raise RuntimeError(
            "FAL_KEY not set. "
            "Use --api hf (free with HF account) or --api prompt-only (no account needed)."
        )
    try:
        import fal_client  # type: ignore
    except ImportError:
        raise RuntimeError("fal-client not installed. Run: pip install fal-client")
    os.environ["FAL_KEY"] = api_key
    result = fal_client.run(
        "fal-ai/flux/schnell",
        arguments={"prompt": prompt, "image_size": "landscape_16_9", "num_images": 1},
    )
    url: str = result["images"][0]["url"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, out_path)


def run_backend(api: str, target: dict, out_path: Path) -> None:
    prompt = _base_prompt(target)
    if api == "stub":
        generate_stub(target, out_path)
    elif api == "hf":
        generate_hf(prompt, out_path)
    elif api == "dall-e-3":
        generate_dalle3(prompt, out_path)
    elif api == "flux":
        generate_flux_fal(prompt, out_path)
    else:
        raise ValueError(f"Unknown api: {api!r}")


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------

def record_attempt(
    director_script: Path,
    task_dir: Path,
    target_id: str,
    prompt: str,
    out_path: Path,
    status: str,
    error: str = "",
) -> bool:
    cmd = [
        sys.executable, str(director_script),
        "--base-dir", str(task_dir.parent.parent),
        "image-asset",
        "--task", task_dir.name,
        "--target-id", target_id,
        "--prompt", prompt,
        "--output-path", str(out_path),
        "--status", status,
    ]
    if error:
        cmd += ["--error", error]
    result = subprocess.run(cmd, check=False, capture_output=True)
    if result.returncode != 0:
        msg = result.stderr.decode(errors="replace").strip() or f"exit {result.returncode}"
        print(f"  ⚠ registration failed for [{target_id}]: {msg}", file=sys.stderr)
        return False
    return True


# ---------------------------------------------------------------------------
# Prompt-only export
# ---------------------------------------------------------------------------

def conversation_prompt_lines(task_dir: Path, targets: list[dict]) -> list[str]:
    if not targets:
        return ["No pre-v1 targets found."]

    lines: list[str] = [
        f"需要生成 {len(targets)} 张图片:",
        "",
    ]
    for index, target in enumerate(targets, start=1):
        current_target_id: str = target_id(target)
        prompt: str = _base_prompt(target)
        try:
            output_label: str = str(target_output_path(task_dir, target))
        except ValueError as exc:
            output_label = f"INVALID OUTPUT PATH: {exc}"
        lines.extend([
            f"{index}. [{current_target_id}] -> 保存到: {output_label}",
            f"   提示词: {prompt}",
            "   推荐工具: Copilot / Ideogram / Firefly",
            "",
        ])
    lines.extend([
        "生成后告诉我文件路径，或直接拖入上述文件夹，我会自动注册。",
        "注册命令示例:",
        f"python3 skills/deck-builder/scripts/generate_images.py --task-dir {task_dir} place --source <image-path> --target-id <target-id>",
    ])
    return lines


def show_prompts(task_dir: Path) -> None:
    targets: list[dict] = read_pre_v1_targets(task_dir)
    print("\n".join(conversation_prompt_lines(task_dir, targets)))


def export_prompts(task_dir: Path) -> None:
    """Write concise manual-generation prompts for each pre-v1 target."""
    targets: list[dict] = read_pre_v1_targets(task_dir)
    if not targets:
        print("No pre-v1 targets found.")
        return

    out_md: Path = task_dir / "image-prompts.md"
    lines: list[str] = [
        "# Image Prompts",
        "",
        *conversation_prompt_lines(task_dir, targets),
        "",
    ]
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"Prompts written to: {out_md}")


# ---------------------------------------------------------------------------
# Place manually downloaded images
# ---------------------------------------------------------------------------

def copy_and_record_source(
    task_dir: Path,
    director_script: Path,
    targets: list[dict],
    requested_target_id: str,
    source_value: str,
) -> bool:
    target: dict | None = target_by_id(targets, requested_target_id)
    if target is None:
        print(f"  ✗ [{requested_target_id}] target not found in image-plan.json")
        return False

    source_path: Path = Path(source_value).expanduser().resolve()
    if not source_path.exists() or source_path.stat().st_size <= 0:
        print(f"  ✗ [{requested_target_id}] source missing or empty: {source_path}")
        return False

    try:
        out_path: Path = target_output_path(task_dir, target)
    except ValueError as exc:
        print(f"  ✗ [{requested_target_id}] invalid output path: {exc}")
        return False
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if source_path != out_path:
        shutil.copy2(source_path, out_path)

    prompt: str = _base_prompt(target)
    if not record_attempt(director_script, task_dir, requested_target_id, prompt, out_path, "success"):
        return False
    action: str = "copied and registered" if source_path != out_path else "registered"
    print(f"  ✓ [{requested_target_id}] {action}: {out_path} ({out_path.stat().st_size // 1024} KB)")
    return True


def parse_sources_json(sources_json: str) -> dict[str, str]:
    try:
        value: object = json.loads(sources_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"--sources must be a JSON object: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("--sources must be a JSON object mapping target_id to source path")
    parsed: dict[str, str] = {}
    for key, source_value in value.items():
        target_name: str = str(key).strip()
        source_text: str = str(source_value).strip()
        if target_name and source_text:
            parsed[target_name] = source_text
    return parsed


def place_manual(
    task_dir: Path,
    director_script: Path,
    source: str = "",
    target_id_value: str = "",
    sources_json: str = "",
) -> None:
    """Register manual images by copying sources or scanning planned output paths."""
    targets: list[dict] = read_pre_v1_targets(task_dir)
    if not targets:
        print("No pre-v1 targets found.")
        return

    if sources_json and source:
        raise ValueError("--sources and --source are mutually exclusive; use one or the other")

    if sources_json:
        source_map: dict[str, str] = parse_sources_json(sources_json)
        found: int = 0
        missing: int = 0
        for requested_target_id, source_value in source_map.items():
            if copy_and_record_source(task_dir, director_script, targets, requested_target_id, source_value):
                found += 1
            else:
                missing += 1
        print(f"\n{found} registered, {missing} missing.")
        return

    if source:
        if not target_id_value:
            raise ValueError("--target-id is required when --source is used")
        copied: bool = copy_and_record_source(task_dir, director_script, targets, target_id_value, source)
        print("\n1 registered, 0 missing." if copied else "\n0 registered, 1 missing.")
        return

    found: int = 0
    missing: int = 0
    for target in targets:
        current_target_id: str = target_id(target)
        prompt: str = _base_prompt(target)
        try:
            out_path: Path = target_output_path(task_dir, target)
        except ValueError as exc:
            print(f"  ✗ [{current_target_id}] invalid output path: {exc}")
            missing += 1
            continue

        if out_path.exists() and out_path.stat().st_size > 0:
            size_kb: int = out_path.stat().st_size // 1024
            if record_attempt(director_script, task_dir, current_target_id, prompt, out_path, "success"):
                print(f"  ✓ [{current_target_id}] registered ({size_kb} KB)")
                found += 1
            else:
                missing += 1
        else:
            print(f"  ✗ [{current_target_id}] not found: {out_path}")
            missing += 1

    print(f"\n{found} recorded, {missing} missing.")
    if missing:
        print("Place missing images and run `place` again.")
    else:
        print("All images placed. Run guard to verify:")
        print(f"  python3 scripts/presentation_director.py guard --task {task_dir.name}")


# ---------------------------------------------------------------------------
# Automatic generation loop
# ---------------------------------------------------------------------------

def generate_targets(task_dir: Path, api: str, director_script: Path) -> None:
    targets: list[dict] = read_pre_v1_targets(task_dir)
    if not targets:
        print("No pre-v1 targets. Nothing to generate.")
        return

    print(f"Generating {len(targets)} image(s) via --api {api} …")
    success_count = fail_count = 0

    for target in targets:
        current_target_id: str = target_id(target)
        prompt: str = _base_prompt(target)
        try:
            out_path: Path = target_output_path(task_dir, target)
        except ValueError as exc:
            print(f"  [{current_target_id}] invalid output path: {exc}", file=sys.stderr)
            fail_count += 1
            continue

        final_status = "failed"

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                print(f"  [{current_target_id}] attempt {attempt}/{MAX_ATTEMPTS} ...", end=" ", flush=True)
                run_backend(api, target, out_path)
                # stub backend produces solid-colour placeholders, not real AI images
                record_status = "stub-placeholder" if api == "stub" else "success"
                if record_attempt(director_script, task_dir, current_target_id, prompt, out_path, record_status):
                    final_status = record_status
                    if api == "stub":
                        print("OK (stub placeholder — replace with a real AI image before delivery)")
                    else:
                        print("OK")
                else:
                    print("OK (image on disk but registration failed — run `place` to re-register)")
                    final_status = record_status
                break
            except Exception as exc:
                err = str(exc)
                record_attempt(director_script, task_dir, current_target_id, prompt, out_path, "failed", err)
                print(f"FAILED  {err}")
                if attempt < MAX_ATTEMPTS:
                    time.sleep(4)

        if final_status == "success":
            success_count += 1
        elif final_status == "stub-placeholder":
            success_count += 1  # on-disk, but counted separately in summary
        else:
            fail_count += 1
            print(f"  [{current_target_id}] FAILED after {MAX_ATTEMPTS} attempts.", file=sys.stderr)

    print(f"\nDone: {success_count} generated, {fail_count} failed.")
    if fail_count:
        print(
            "Tip: use --api prompt-only to get prompts for free online tools, "
            "then run `place` after downloading.",
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate or export AI image prompts for Presentation Director.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--task-dir", help="Path to PPTX/<task-slug>/")
    parser.add_argument(
        "--api",
        choices=["hf", "stub", "dall-e-3", "flux", "prompt-only"],
        default="prompt-only",
        help=(
            "hf: Hugging Face FLUX free (HF_TOKEN) | "
            "stub: solid-color PNG for testing | "
            "dall-e-3: OpenAI (OPENAI_API_KEY) | "
            "flux: fal.ai (FAL_KEY) | "
            "prompt-only: export prompts to image-prompts.md (default)"
        ),
    )
    parser.add_argument(
        "--director-script",
        default=str(Path(__file__).resolve().parent / "presentation_director.py"),
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=["show", "place"],
        help="show: print prompts to stdout | place: record manually downloaded images into image-assets.json",
    )
    parser.add_argument("--source", default="", help="Source image path for one manual placement.")
    parser.add_argument("--target-id", default="", help="Target id used with --source.")
    parser.add_argument(
        "--sources",
        default="",
        help='JSON object mapping target ids to source image paths, e.g. \'{"cover":"~/cover.png"}\'.',
    )
    args = parser.parse_args()

    if not args.task_dir:
        parser.error("--task-dir is required")

    task_dir = Path(args.task_dir).expanduser().resolve()
    if not task_dir.is_dir():
        print(f"Task directory not found: {task_dir}", file=sys.stderr)
        sys.exit(1)

    director_script = Path(args.director_script).expanduser().resolve()
    if not director_script.exists():
        print(f"Director script not found: {director_script}", file=sys.stderr)
        sys.exit(1)

    if args.command == "show":
        show_prompts(task_dir)
    elif args.command == "place":
        try:
            place_manual(task_dir, director_script, args.source, args.target_id, args.sources)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            sys.exit(2)
    elif args.api == "prompt-only":
        export_prompts(task_dir)
    else:
        generate_targets(task_dir, args.api, director_script)


if __name__ == "__main__":
    main()
