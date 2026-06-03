"""
generate_images.py — pre-v1 AI image generation for Presentation Director.

Reads image-plan.json, generates each pre-v1 target, records results via
`presentation_director.py image-asset`. Supports:

  --api stub       : write solid-color PNG (no API key needed, for testing)
  --api dall-e-3   : call OpenAI DALL-E 3 (requires OPENAI_API_KEY env var)
  --api flux       : call fal.ai Flux (requires FAL_KEY env var)

Usage:
  python3 generate_images.py --task-dir PPTX/<slug> --api stub
  python3 generate_images.py --task-dir PPTX/<slug> --api dall-e-3
"""
from __future__ import annotations

import argparse
import os
import json
import struct
import zlib
import time
import subprocess
import sys
import urllib.request
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


# ---------------------------------------------------------------------------
# Minimal PNG writer (no Pillow needed for stub mode)
# ---------------------------------------------------------------------------

def _make_png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


def write_solid_png(path: Path, width: int, height: int, rgb: tuple[int, int, int]) -> None:
    r, g, b = rgb
    path.parent.mkdir(parents=True, exist_ok=True)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    row = bytes([0] + [r, g, b] * width)
    raw = b"".join(row for _ in range(height))
    idat = zlib.compress(raw)
    with path.open("wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(_make_png_chunk(b"IHDR", ihdr))
        f.write(_make_png_chunk(b"IDAT", idat))
        f.write(_make_png_chunk(b"IEND", b""))


# ---------------------------------------------------------------------------
# Image generation backends
# ---------------------------------------------------------------------------

def generate_stub(target: dict, out_path: Path) -> None:
    slide_role: str = str(target.get("slide_role", "cover"))
    color: tuple[int, int, int] = STUB_COLORS.get(slide_role, DEFAULT_STUB_COLOR)
    write_solid_png(out_path, 1920, 1080, color)


def generate_dalle3(prompt: str, out_path: Path) -> None:
    api_key: str = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set. Set it or use --api stub for testing.")
    try:
        import openai  # type: ignore
    except ImportError:
        raise RuntimeError("openai package not installed. Run: pip install openai")
    client = openai.OpenAI(api_key=api_key)
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1792x1024",
        quality="standard",
        n=1,
    )
    url: str = response.data[0].url
    out_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, out_path)


def generate_flux(prompt: str, out_path: Path) -> None:
    api_key: str = os.environ.get("FAL_KEY", "")
    if not api_key:
        raise RuntimeError("FAL_KEY is not set. Set it or use --api stub for testing.")
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
    if api == "stub":
        generate_stub(target, out_path)
    elif api == "dall-e-3":
        generate_dalle3(str(target.get("prompt_draft", "")), out_path)
    elif api == "flux":
        generate_flux(str(target.get("prompt_draft", "")), out_path)
    else:
        raise ValueError(f"Unknown api: {api!r}. Choose stub, dall-e-3, or flux.")


# ---------------------------------------------------------------------------
# Recording via presentation_director.py image-asset CLI
# ---------------------------------------------------------------------------

def record_attempt(
    director_script: Path,
    task_dir: Path,
    target_id: str,
    prompt: str,
    out_path: Path,
    status: str,
    error: str = "",
) -> None:
    cmd = [
        sys.executable,
        str(director_script),
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
    subprocess.run(cmd, check=False)


# ---------------------------------------------------------------------------
# Main generation loop
# ---------------------------------------------------------------------------

def generate_targets(task_dir: Path, api: str, director_script: Path) -> None:
    plan_path: Path = task_dir / "image-plan.json"
    if not plan_path.exists():
        print(f"No image-plan.json found at {plan_path}. Nothing to generate.")
        return

    with plan_path.open(encoding="utf-8") as f:
        plan: dict = json.load(f)

    targets: list[dict] = [
        t for t in plan.get("targets", [])
        if isinstance(t, dict) and str(t.get("phase", "pre-v1")) == "pre-v1"
    ]

    if not targets:
        print("No pre-v1 targets in image-plan.json. Nothing to generate.")
        return

    print(f"Generating {len(targets)} pre-v1 image(s) via api={api!r} …")
    success_count = 0
    fail_count = 0

    for target in targets:
        target_id: str = str(target.get("id", "unknown"))
        prompt: str = str(target.get("prompt_draft", "Abstract background"))
        raw_path: str = str(target.get("output_path", f"assets/images/{target_id}.png"))
        out_path: Path = Path(raw_path) if Path(raw_path).is_absolute() else task_dir / raw_path

        final_status = "failed"
        last_error = ""

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                print(f"  [{target_id}] attempt {attempt}/{MAX_ATTEMPTS} …", end=" ", flush=True)
                run_backend(api, target, out_path)
                record_attempt(director_script, task_dir, target_id, prompt, out_path, "success")
                final_status = "success"
                print("✓")
                break
            except Exception as exc:
                last_error = str(exc)
                record_attempt(director_script, task_dir, target_id, prompt, out_path, "failed", last_error)
                print(f"✗  {last_error}")
                if attempt < MAX_ATTEMPTS:
                    time.sleep(3)

        if final_status == "success":
            success_count += 1
        else:
            fail_count += 1
            print(f"  [{target_id}] FAILED after {MAX_ATTEMPTS} attempts.", file=sys.stderr)

    print(f"\nDone: {success_count} succeeded, {fail_count} failed.")
    if fail_count:
        print("Fix failures before running guard. Do not proceed with CSS gradient fallback.", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate pre-v1 AI images for Presentation Director.")
    parser.add_argument("--task-dir", required=True, help="Path to PPTX/<task-slug>/")
    parser.add_argument("--api", choices=["stub", "dall-e-3", "flux"], default="stub",
                        help="Image generation backend (default: stub)")
    parser.add_argument("--director-script",
                        default=str(Path(__file__).resolve().parent / "presentation_director.py"),
                        help="Path to presentation_director.py")
    args = parser.parse_args()

    task_dir = Path(args.task_dir).expanduser().resolve()
    if not task_dir.is_dir():
        print(f"Task directory not found: {task_dir}", file=sys.stderr)
        sys.exit(1)

    director_script = Path(args.director_script).expanduser().resolve()
    if not director_script.exists():
        print(f"Director script not found: {director_script}", file=sys.stderr)
        sys.exit(1)

    generate_targets(task_dir, args.api, director_script)


if __name__ == "__main__":
    main()
