"""Render a deck page by page with the office app already on the computer (PowerPoint, WPS or
Keynote; LibreOffice only as a last resort) and run a structural layout check on the file itself.

The report is written next to the PPTX in its version folder; export only accepts a version whose
report passed.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
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


MAC_POWERPOINT = Path("/Applications/Microsoft PowerPoint.app")
MAC_KEYNOTE = Path("/Applications/Keynote.app")
# Sandboxed Mac apps can read and write their own container without asking the user for file access.
MAC_CONTAINERS = {
    "powerpoint": Path.home() / "Library/Containers/com.microsoft.Powerpoint/Data/Documents",
    "keynote": Path.home() / "Library/Containers/com.apple.iWork.Keynote/Data/Documents",
}


def _windows_progid_exists(progid: str) -> bool:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, progid):
            return True
    except OSError:
        return False


def find_pptx_renderer() -> tuple[str, str] | None:
    """The office app already on this computer, preferred over LibreOffice: (kind, display name)."""
    forced = os.environ.get("PD_PPTX_RENDERER")
    if sys.platform == "darwin":
        options = [
            ("powerpoint-mac", "PowerPoint", MAC_POWERPOINT.is_dir()),
            ("keynote", "Keynote", MAC_KEYNOTE.is_dir()),
        ]
    elif os.name == "nt":
        options = [
            ("powerpoint-win", "PowerPoint", _windows_progid_exists("PowerPoint.Application")),
            ("wps", "WPS", _windows_progid_exists("KWPP.Application")),
        ]
    else:
        options = []
    soffice = find_soffice()
    options.append(
        ("libreoffice", soffice_version(soffice) if soffice else "LibreOffice", soffice is not None)
    )
    for kind, name, available in options:
        if available and (forced is None or forced == kind):
            return kind, name
    return None


def _osascript(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["osascript", "-e", script], capture_output=True, text=True, timeout=300, check=False
    )


def _mac_app_to_pdf(app: str, pptx: Path, pdf: Path) -> None:
    work = MAC_CONTAINERS[app] / "PresentationDirector" / uuid.uuid4().hex
    work.mkdir(parents=True, exist_ok=True)
    try:
        src, out = work / "deck.pptx", work / "deck.pdf"
        shutil.copyfile(pptx, src)
        if app == "powerpoint":
            script = f"""
set wasRunning to application "Microsoft PowerPoint" is running
with timeout of 240 seconds
  tell application "Microsoft PowerPoint"
    open POSIX file "{src}"
    -- The file just opened is the active presentation; PowerPoint's "whose full name" lookup is unreliable.
    save active presentation in POSIX file "{out}" as save as PDF
    close active presentation saving no
    if not wasRunning then quit saving no
  end tell
end timeout"""
        else:
            script = f"""
set wasRunning to application "Keynote" is running
with timeout of 240 seconds
  tell application "Keynote"
    set theDoc to open POSIX file "{src}"
    export theDoc to POSIX file "{out}" as PDF
    close theDoc saving no
    if not wasRunning then quit
  end tell
end timeout"""
        _osascript(script)
        if out.is_file():
            shutil.copyfile(out, pdf)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _windows_com_to_pdf(progid: str, pptx: Path, pdf: Path) -> None:
    # PowerPoint and WPS share the PowerPoint object model; 32 = ppSaveAsPDF.
    script = (
        "$ErrorActionPreference='Stop';"
        f"$app=New-Object -ComObject {progid};"
        "$p=$app.Presentations.Open($env:PD_IN,-1,0,0);"
        "try{$p.SaveAs($env:PD_OUT,32)}catch{$p.ExportAsFixedFormat($env:PD_OUT,2)};"
        "$p.Close();if($app.Presentations.Count -eq 0){$app.Quit()}"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        timeout=300,
        check=False,
        env={**os.environ, "PD_IN": str(pptx.resolve()), "PD_OUT": str(pdf.resolve())},
    )


def _libreoffice_to_pdf(soffice: Path, pptx: Path, pdf: Path, profile_dir: Path) -> None:
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
        produced = Path(tmp) / (pptx.stem + ".pdf")
        if produced.is_file():
            shutil.copyfile(produced, pdf)


def pptx_to_pdf(kind: str, pptx: Path, pdf: Path, profile_dir: Path) -> None:
    if kind == "powerpoint-mac":
        _mac_app_to_pdf("powerpoint", pptx, pdf)
    elif kind == "keynote":
        _mac_app_to_pdf("keynote", pptx, pdf)
    elif kind == "powerpoint-win":
        _windows_com_to_pdf("PowerPoint.Application", pptx, pdf)
    elif kind == "wps":
        _windows_com_to_pdf("KWPP.Application", pptx, pdf)
    else:
        soffice = find_soffice()
        if soffice:
            _libreoffice_to_pdf(soffice, pptx, pdf, profile_dir)


def pdf_to_images(pdf_path: Path, slides_dir: Path, scale: float = 1.5) -> list[Path]:
    import pypdfium2 as pdfium

    slides_dir.mkdir(parents=True, exist_ok=True)
    if not pdf_path.is_file():
        return []
    pdf = pdfium.PdfDocument(str(pdf_path))
    images: list[Path] = []
    for i in range(len(pdf)):
        image_path = slides_dir / f"slide-{i + 1:02d}.png"
        pdf[i].render(scale=scale).to_pil().save(image_path)
        images.append(image_path)
    pdf.close()
    return images


def render_pages(pptx: Path, out_dir: Path, kind: str, profile_dir: Path) -> list[Path]:
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "deck.pdf"
        pptx_to_pdf(kind, pptx, pdf, profile_dir)
        return pdf_to_images(pdf, out_dir / "slides")


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
    renderer = find_pptx_renderer()
    issues = structure_issues(pptx)
    if renderer is None:
        report = CheckReport(version, "none", expected_pages, 0, issues=issues)
        report.issues.append("没有找到 PowerPoint、WPS、Keynote 或 LibreOffice，无法逐页出图检查")
    else:
        kind, name = renderer
        images = render_pages(pptx, out_dir, kind, profile_dir)
        sheet = out_dir / "contact-sheet.png"
        contact_sheet(images, sheet)
        report = CheckReport(
            version,
            name,
            expected_pages,
            len(images),
            images=[str(p) for p in images],
            contact_sheet=str(sheet) if images else "",
            issues=issues,
        )
        if len(images) != expected_pages:
            report.issues.append(f"{name} 出图得到 {len(images)} 页，应为 {expected_pages} 页")
    return report


# ---- HTML decks: checked with the Chromium browser already on the machine (Edge on Windows) ----

CANDIDATE_BROWSERS = (
    Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
    / "Microsoft/Edge/Application/msedge.exe",
    Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
    / "Microsoft/Edge/Application/msedge.exe",
    Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
    / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
)


def find_browser() -> Path | None:
    configured = os.environ.get("PD_BROWSER")
    if configured and Path(configured).is_file():
        return Path(configured)
    for candidate in CANDIDATE_BROWSERS:
        if candidate.is_file():
            return candidate
    for name in ("msedge", "google-chrome", "chromium", "chromium-browser", "chrome"):
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


def _headless(browser: Path, profile_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    # A separate profile keeps the headless run apart from the user's own open browser windows.
    profile_dir.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={profile_dir}",
            "--window-size=1600,900",
            "--virtual-time-budget=5000",
            *args,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        check=False,
    )


def html_issues(html: Path, browser: Path, profile_dir: Path) -> tuple[int, list[str]]:
    """Slide count and overflow problems as measured by the deck's own ?pd-check script."""
    import html as html_lib
    import re

    dom = _headless(
        browser, profile_dir, "--dump-dom", html.resolve().as_uri() + "?pd-check"
    ).stdout
    match = re.search(r'data-pd-check="([^"]*)"', dom)
    if not match:
        return 0, ["浏览器没有返回版面检查结果"]
    results = json.loads(html_lib.unescape(match.group(1)))
    issues = [
        f"第 {r['slide']} 页（HTML）：内容超出页面（「{'」「'.join(r['overflow'])}」）"
        for r in results
        if r["overflow"]
    ]
    return len(results), issues


def render_html_pages(html: Path, out_dir: Path, browser: Path, profile_dir: Path) -> list[Path]:
    import pypdfium2 as pdfium

    slides_dir = out_dir / "html-slides"
    slides_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / "deck.pdf"
        _headless(
            browser,
            profile_dir,
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            html.resolve().as_uri(),
        )
        if not pdf_path.is_file():
            return []
        pdf = pdfium.PdfDocument(str(pdf_path))
        images = []
        for i in range(len(pdf)):
            image_path = slides_dir / f"slide-{i + 1:02d}.png"
            pdf[i].render(scale=1.0).to_pil().save(image_path)
            images.append(image_path)
        pdf.close()
    return images


def check_html(html: Path, version: str, expected_pages: int, profile_dir: Path) -> CheckReport:
    out_dir = html.parent
    browser = find_browser()
    if browser is None:
        return CheckReport(
            version, "none", expected_pages, 0, issues=["未找到 Edge 或 Chrome，无法检查 HTML 演示"]
        )
    measured, issues = html_issues(html, browser, profile_dir)
    images = render_html_pages(html, out_dir, browser, profile_dir)
    sheet = out_dir / "html-contact-sheet.png"
    contact_sheet(images, sheet)
    report = CheckReport(
        version,
        browser.stem,
        expected_pages,
        len(images),
        images=[str(p) for p in images],
        contact_sheet=str(sheet) if images else "",
        issues=issues,
    )
    if measured != expected_pages:
        report.issues.append(f"HTML 检查到 {measured} 页，应为 {expected_pages} 页")
    if len(images) != expected_pages:
        report.issues.append(f"HTML 打印得到 {len(images)} 页，应为 {expected_pages} 页")
    return report
