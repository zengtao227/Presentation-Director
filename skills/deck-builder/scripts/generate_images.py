"""
generate_images.py — AI image generation / prompt export for Presentation Director.

AUTOMATIC backends (no human involvement):
  --api stub        Solid-color PNG for testing, no API key needed
  --api hf          Hugging Face FLUX.1-schnell, free with HF_TOKEN
                    (free account at huggingface.co, token from Settings → Access Tokens)
  --api dall-e-3    OpenAI DALL-E 3  (OPENAI_API_KEY, ~$0.04/image)
  --api flux        fal.ai Flux      (FAL_KEY, ~$0.003/image)

MANUAL workflow — best zero-cost option:
  --api prompt-only  Export optimized prompts to image-prompts.md.
                     Paste into any free online tool, download image,
                     then run `place` to register it.

REGISTER manually downloaded images:
  place              Scan assets/images/ for plan targets and record them.

Free online tools that accept these prompts (no API key needed):
  • Microsoft Copilot / Bing Image Creator  →  copilot.microsoft.com  (DALL-E 3, generous free)
  • Google ImageFX                          →  aitestkitchen.withgoogle.com/tools/image-fx
  • Adobe Firefly                           →  firefly.adobe.com  (25 free credits/month)
  • Ideogram                                →  ideogram.ai  (free tier, good quality)
  • Leonardo.ai                             →  leonardo.ai  (free daily credits)

Usage:
  python3 generate_images.py --task-dir PPTX/<slug> --api stub
  python3 generate_images.py --task-dir PPTX/<slug> --api hf
  python3 generate_images.py --task-dir PPTX/<slug> --api prompt-only
  python3 generate_images.py --task-dir PPTX/<slug> place
"""
from __future__ import annotations

import argparse
import json
import os
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


def _platform_prompts(target: dict) -> dict[str, str]:
    """Return platform-specific prompt variants for manual generation."""
    base = _base_prompt(target)
    constraints = (
        "No text, no letters, no people, no faces, no logos, no watermarks. "
        "1920×1080 landscape, presentation slide background, suitable for text overlay."
    )
    return {
        # Microsoft Copilot / Bing Image Creator (best free option — DALL-E 3)
        "copilot_bing": f"{base}. {constraints}",

        # Google ImageFX, Adobe Firefly, Ideogram, Leonardo.ai
        "generic": f"{base}. {constraints}",

        # Midjourney (Discord bot)
        "midjourney": (
            f"{base}, presentation background, abstract texture, cinematic lighting "
            f"--ar 16:9 --v 6.1 --style raw "
            f"--no text, letters, people, faces, logos, watermarks"
        ),

        # Stable Diffusion (Automatic1111 / ComfyUI)
        "sd_positive": (
            f"{base}, high resolution, 8k, professional photography, dramatic lighting, "
            f"16:9 aspect ratio"
        ),
        "sd_negative": NEGATIVE_PROMPT,
    }


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
        data = resp.read()
    ct = resp.headers.get("Content-Type", "")
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
) -> None:
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
    subprocess.run(cmd, check=False)


# ---------------------------------------------------------------------------
# Prompt-only export
# ---------------------------------------------------------------------------

def export_prompts(task_dir: Path) -> None:
    """Write image-prompts.md with platform-specific prompts for each target."""
    plan_path = task_dir / "image-plan.json"
    if not plan_path.exists():
        print(f"No image-plan.json at {plan_path}.")
        return

    with plan_path.open(encoding="utf-8") as f:
        plan: dict = json.load(f)

    targets = [
        t for t in plan.get("targets", [])
        if isinstance(t, dict) and str(t.get("phase", "pre-v1")) == "pre-v1"
    ]
    if not targets:
        print("No pre-v1 targets found.")
        return

    out_md = task_dir / "image-prompts.md"
    lines: list[str] = [
        "# Image Prompts for Manual Generation",
        "",
        "## Recommended free tools (no API key needed)",
        "",
        "| Tool | URL | Quality | Limit |",
        "|---|---|---|---|",
        "| **Microsoft Copilot** | copilot.microsoft.com | ★★★★★ (DALL-E 3) | Generous daily free |",
        "| **Google ImageFX** | aitestkitchen.withgoogle.com/tools/image-fx | ★★★★ | Free, Google account |",
        "| **Ideogram** | ideogram.ai | ★★★★ | Free tier |",
        "| **Adobe Firefly** | firefly.adobe.com | ★★★★ | 25 free credits/month |",
        "| **Leonardo.ai** | leonardo.ai | ★★★★ | Free daily credits |",
        "",
        "**Tip:** Microsoft Copilot is the easiest — no upload limit, no subscription, DALL-E 3 quality.",
        "",
        "## After generating each image",
        "",
        "Download it and save to the path shown below, then run:",
        "```bash",
        f"python3 skills/deck-builder/scripts/generate_images.py --task-dir {task_dir} place",
        "```",
        "",
        "---",
        "",
    ]

    for target in targets:
        target_id = str(target.get("id", "unknown"))
        out_path = str(target.get("output_path", f"assets/images/{target_id}.png"))
        prompts = _platform_prompts(target)
        slide_role = str(target.get("slide_role", "cover"))

        lines += [
            f"## Image: `{target_id}`",
            f"**Save to:** `{task_dir / out_path}`",
            f"**Slide role:** {slide_role} &nbsp;|&nbsp; **Required size:** 1920×1080 px (16:9)",
            "",
            "### Use this prompt (works for Copilot, Firefly, Ideogram, Leonardo)",
            "```",
            prompts["generic"],
            "```",
            "",
            "### Midjourney (Discord)",
            "```",
            prompts["midjourney"],
            "```",
            "",
            "### Stable Diffusion / ComfyUI",
            "**Positive prompt:**",
            "```",
            prompts["sd_positive"],
            "```",
            "**Negative prompt:**",
            "```",
            prompts["sd_negative"],
            "```",
            "",
            "---",
            "",
        ]

    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"✓ Prompts written to: {out_md}")
    print()
    print("Steps:")
    for target in targets:
        target_id = str(target.get("id", "unknown"))
        out_path = str(target.get("output_path", f"assets/images/{target_id}.png"))
        print(f"  1. Open image-prompts.md, copy prompt for [{target_id}]")
        print(f"  2. Paste into copilot.microsoft.com or any tool above")
        print(f"  3. Download image → save to: {task_dir / out_path}")
    print()
    print(f"  4. Run: python3 {Path(__file__).name} --task-dir {task_dir} place")


# ---------------------------------------------------------------------------
# Place manually downloaded images
# ---------------------------------------------------------------------------

def place_manual(task_dir: Path, director_script: Path) -> None:
    """Scan assets/images/ for files matching plan targets and record them."""
    plan_path = task_dir / "image-plan.json"
    if not plan_path.exists():
        print(f"No image-plan.json at {plan_path}.")
        return

    with plan_path.open(encoding="utf-8") as f:
        plan: dict = json.load(f)

    targets = [
        t for t in plan.get("targets", [])
        if isinstance(t, dict) and str(t.get("phase", "pre-v1")) == "pre-v1"
    ]

    found = missing = 0
    for target in targets:
        target_id = str(target.get("id", "unknown"))
        prompt = _base_prompt(target)
        raw_path = str(target.get("output_path", f"assets/images/{target_id}.png"))
        out_path = Path(raw_path) if Path(raw_path).is_absolute() else task_dir / raw_path

        if out_path.exists() and out_path.stat().st_size > 0:
            record_attempt(director_script, task_dir, target_id, prompt, out_path, "success")
            print(f"  ✓ [{target_id}] recorded ({out_path.stat().st_size // 1024} KB)")
            found += 1
        else:
            print(f"  ✗ [{target_id}] not found: {out_path}")
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
    plan_path = task_dir / "image-plan.json"
    if not plan_path.exists():
        print(f"No image-plan.json at {plan_path}. Nothing to generate.")
        return

    with plan_path.open(encoding="utf-8") as f:
        plan: dict = json.load(f)

    targets = [
        t for t in plan.get("targets", [])
        if isinstance(t, dict) and str(t.get("phase", "pre-v1")) == "pre-v1"
    ]
    if not targets:
        print("No pre-v1 targets. Nothing to generate.")
        return

    print(f"Generating {len(targets)} image(s) via --api {api} …")
    success_count = fail_count = 0

    for target in targets:
        target_id = str(target.get("id", "unknown"))
        prompt = _base_prompt(target)
        raw_path = str(target.get("output_path", f"assets/images/{target_id}.png"))
        out_path = Path(raw_path) if Path(raw_path).is_absolute() else task_dir / raw_path

        final_status = "failed"

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                print(f"  [{target_id}] attempt {attempt}/{MAX_ATTEMPTS} …", end=" ", flush=True)
                run_backend(api, target, out_path)
                record_attempt(director_script, task_dir, target_id, prompt, out_path, "success")
                final_status = "success"
                print("✓")
                break
            except Exception as exc:
                err = str(exc)
                record_attempt(director_script, task_dir, target_id, prompt, out_path, "failed", err)
                print(f"✗  {err}")
                if attempt < MAX_ATTEMPTS:
                    time.sleep(4)

        if final_status == "success":
            success_count += 1
        else:
            fail_count += 1
            print(f"  [{target_id}] FAILED after {MAX_ATTEMPTS} attempts.", file=sys.stderr)

    print(f"\nDone: {success_count} succeeded, {fail_count} failed.")
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
        choices=["place"],
        help="place: record manually downloaded images into image-assets.json",
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

    if args.command == "place":
        place_manual(task_dir, director_script)
    elif args.api == "prompt-only":
        export_prompts(task_dir)
    else:
        generate_targets(task_dir, args.api, director_script)


if __name__ == "__main__":
    main()
