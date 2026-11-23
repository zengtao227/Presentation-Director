"""Collect third-party license texts from the staged Windows payload into one notices file."""

from __future__ import annotations

import json
import sys
from pathlib import Path

LICENSE_PREFIXES = ("LICENSE", "LICENCE", "COPYING", "NOTICE")


def license_texts(folder: Path) -> list[str]:
    texts = []
    for path in sorted(folder.iterdir()):
        if path.is_file() and path.name.upper().startswith(LICENSE_PREFIXES):
            texts.append(path.read_text(encoding="utf-8", errors="replace").strip())
    return texts


def main(files: Path, out: Path) -> None:
    sections: list[str] = []

    def add(title: str, texts: list[str]) -> None:
        if texts:
            sections.append(f"==== {title} ====\n\n" + "\n\n".join(texts))

    add("Python (embeddable distribution)", license_texts(files / "python"))
    add("Node.js", license_texts(files / "node"))
    for dist in sorted((files / "python" / "Lib" / "site-packages").glob("*.dist-info")):
        texts = license_texts(dist)
        lic_dir = dist / "licenses"
        if lic_dir.is_dir():
            for path in sorted(lic_dir.rglob("*")):
                if path.is_file():
                    texts.append(path.read_text(encoding="utf-8", errors="replace").strip())
        add(dist.name.removesuffix(".dist-info"), texts)
    for pkg in sorted((files / "engine" / "generator" / "node_modules").rglob("package.json")):
        owner = pkg.parent.parent.name
        # Only package roots: node_modules/<pkg> or node_modules/@scope/<pkg>.
        if owner != "node_modules" and not owner.startswith("@"):
            continue
        meta = json.loads(pkg.read_text(encoding="utf-8"))
        title = f"{meta.get('name')} {meta.get('version')} ({meta.get('license')})"
        add(title, license_texts(pkg.parent))
    add("pakco-html", license_texts(files / "skills" / "html-deck" / "pakco-html"))
    header = (
        "Presentation Director includes the third-party components listed below.\n"
        "Each component is licensed under its own terms, reproduced here.\n"
        "LibreOffice is not bundled; the installer downloads the official package\n"
        "from The Document Foundation.\n\n"
    )
    out.write_text(header + "\n\n".join(sections) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
