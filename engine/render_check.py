"""Render a PPTX page by page with LibreOffice and run a structural layout check on the file itself.

The report is written next to the PPTX in its version folder; export only accepts a version whose
report passed.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

EMU_PER_PT = 12700
CANDIDATE_SOFFICE = (
    Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "LibreOffice/program/soffice.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
    / "LibreOffice/program/soffice.exe",
    Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
)


@dataclass
class CheckReport:
    version: str
    renderer: str
    expected_pages: int
    pages: int
    images: list[str] = field(default_factory=list)
    contact_sheet: str = ""
    issues: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.pages == self.expected_pages and not self.issues

    def to_json(self) -> dict[str, object]:
        data = asdict(self)
        data["passed"] = self.passed
        return data


def find_soffice() -> Path | None:
    configured = os.environ.get("PD_SOFFICE")
    if configured and Path(configured).is_file():
        return Path(configured)
    on_path = shutil.which("soffice") or shutil.which("soffice.exe")
    if on_path:
        return Path(on_path)
    for candidate in CANDIDATE_SOFFICE:
        if candidate.is_file():
            return candidate
    return None


def soffice_version(soffice: Path) -> str:
    # On Windows soffice.exe is a GUI program and prints nothing; its console twin soffice.com does.
    console = soffice.with_suffix(".com")
    if soffice.suffix.lower() == ".exe" and console.is_file():
        soffice = console
    try:
        out = subprocess.run(
            [str(soffice), "--version"], capture_output=True, text=True, timeout=60
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        return "LibreOffice (version unknown)"
    return " ".join(out.split()[:2]) or "LibreOffice"


def render_pages(pptx: Path, out_dir: Path, soffice: Path, profile_dir: Path) -> list[Path]:
    import pypdfium2 as pdfium

    slides_dir = out_dir / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)
    profile_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        # A private profile keeps headless runs independent of the user's own LibreOffice settings.
        subprocess.run(
            [
                str(soffice),
                f"-env:UserInstallation={profile_dir.resolve().as_uri()}",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                tmp,
                str(pptx),
            ],
            capture_output=True,
            timeout=300,
            check=False,
        )
        pdf_path = Path(tmp) / (pptx.stem + ".pdf")
        if not pdf_path.is_file():
            return []
        pdf = pdfium.PdfDocument(str(pdf_path))
        images: list[Path] = []
        for i in range(len(pdf)):
            image_path = slides_dir / f"slide-{i + 1:02d}.png"
            pdf[i].render(scale=1.5).to_pil().save(image_path)
            images.append(image_path)
        pdf.close()
    return images


def contact_sheet(images: list[Path], target: Path, columns: int = 3) -> None:
    from PIL import Image

    thumbs = []
    for path in images:
        with Image.open(path) as im:
            im.thumbnail((640, 360))
            thumbs.append(im.copy())
    if not thumbs:
        return
    w, h = thumbs[0].size
    rows = math.ceil(len(thumbs) / columns)
    gap = 12
    sheet = Image.new(
        "RGB", (columns * w + (columns + 1) * gap, rows * h + (rows + 1) * gap), "#e5e7eb"
    )
    for i, thumb in enumerate(thumbs):
        x = gap + (i % columns) * (w + gap)
        y = gap + (i // columns) * (h + gap)
        sheet.paste(thumb, (x, y))
    sheet.save(target)


def _text_width_em(text: str) -> float:
    # East Asian characters are about one em wide; Latin letters, digits and spaces about half.
    return sum(1.0 if ord(ch) >= 0x2E80 else 0.55 for ch in text)


def _estimated_text_height_pt(shape: object) -> tuple[float, float]:
    frame = shape.text_frame  # type: ignore[attr-defined]
    inner_w = (shape.width - (frame.margin_left or 0) - (frame.margin_right or 0)) / EMU_PER_PT  # type: ignore[attr-defined]
    inner_h = (shape.height - (frame.margin_top or 0) - (frame.margin_bottom or 0)) / EMU_PER_PT  # type: ignore[attr-defined]
    total = 0.0
    for para in frame.paragraphs:
        sizes = [r.font.size.pt for r in para.runs if r.font.size is not None]
        size = max(sizes) if sizes else 18.0
        text = "".join(r.text for r in para.runs)
        ppr = para._p.pPr
        indent = 18.0 if ppr is not None and int(ppr.get("marL", "0")) > 0 else 0.0
        usable = max(inner_w - indent, size)
        lines = max(1, math.ceil(_text_width_em(text) * size / usable)) if text else 1
        space_after = para.space_after.pt if para.space_after is not None else 0.0
        total += lines * size * 1.2 + space_after
    return total, inner_h


def structure_issues(pptx: Path) -> list[str]:
    from pptx import Presentation

    prs = Presentation(str(pptx))
    slide_w, slide_h = prs.slide_width, prs.slide_height
    tolerance = EMU_PER_PT * 2
    issues: list[str] = []
    for index, slide in enumerate(prs.slides, start=1):
        for shape in slide.shapes:
            if shape.left is None or shape.width is None:
                continue
            right = shape.left + shape.width
            bottom = shape.top + shape.height
            if (
                shape.left < -tolerance
                or shape.top < -tolerance
                or right > slide_w + tolerance
                or bottom > slide_h + tolerance
            ):
                issues.append(f"第 {index} 页：「{shape.name}」超出页面范围")
            if not shape.has_text_frame or not shape.text_frame.text.strip():
                continue
            needed, available = _estimated_text_height_pt(shape)
            if needed > available * 1.15:
                snippet = shape.text_frame.text.strip().splitlines()[0][:20]
                issues.append(
                    f"第 {index} 页：文字可能溢出文本框（「{snippet}…」约需 {needed:.0f}pt，框高 {available:.0f}pt）"
                )
    return issues


def check(pptx: Path, version: str, expected_pages: int, profile_dir: Path) -> CheckReport:
    out_dir = pptx.parent
    soffice = find_soffice()
    issues = structure_issues(pptx)
    if soffice is None:
        report = CheckReport(version, "none", expected_pages, 0, issues=issues)
        report.issues.append("未找到 LibreOffice，无法逐页渲染检查")
    else:
        images = render_pages(pptx, out_dir, soffice, profile_dir)
        sheet = out_dir / "contact-sheet.png"
        contact_sheet(images, sheet)
        report = CheckReport(
            version,
            soffice_version(soffice),
            expected_pages,
            len(images),
            images=[str(p) for p in images],
            contact_sheet=str(sheet) if images else "",
            issues=issues,
        )
        if len(images) != expected_pages:
            report.issues.append(f"渲染得到 {len(images)} 页，应为 {expected_pages} 页")
    (out_dir / "check-report.json").write_text(
        json.dumps(report.to_json(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report
