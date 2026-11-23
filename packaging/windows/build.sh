#!/usr/bin/env bash
# Builds the Windows x64 package (ZIP: Setup.cmd + install.ps1 + files/) on macOS or Linux.
# Downloads are pinned and cached in packaging/windows/.cache; output goes to packaging/windows/out.
set -euo pipefail

PY_VER="3.12.10"
NODE_VER="22.23.4"
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
CACHE="$HERE/.cache"
OUT="$HERE/out"
VERSION="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$ROOT/engine/__init__.py")"
NAME="PresentationDirector-win-x64-$VERSION"
STAGE="$OUT/stage/$NAME"
FILES="$STAGE/files"

mkdir -p "$CACHE" "$OUT"
case "$STAGE" in "$HERE"/out/stage/*) ;; *) echo "unexpected stage path" >&2; exit 1 ;; esac
rm -rf "$STAGE"
mkdir -p "$FILES"

fetch() { # url file
  [ -s "$CACHE/$2" ] || curl -fsSL "$1" -o "$CACHE/$2"
}

echo "== Python $PY_VER (embeddable)"
fetch "https://www.python.org/ftp/python/$PY_VER/python-$PY_VER-embed-amd64.zip" "python-$PY_VER-embed-amd64.zip"
mkdir -p "$FILES/python"
unzip -q "$CACHE/python-$PY_VER-embed-amd64.zip" -d "$FILES/python"
PTH="$(ls "$FILES"/python/python3*._pth)"
# The embeddable build ignores PYTHONPATH; list the app root and site-packages here instead.
printf 'python312.zip\n.\n..\nLib\\site-packages\nimport site\n' > "$PTH"

echo "== Python packages (win_amd64, from uv.lock)"
REQ="$OUT/requirements-engine.txt"
(cd "$ROOT" && uv export --frozen --extra engine --no-hashes --no-emit-project --no-dev -o "$REQ" >/dev/null)
uv pip install --quiet --target "$FILES/python/Lib/site-packages" \
  --python-platform x86_64-pc-windows-msvc --python-version 3.12 --only-binary :all: -r "$REQ"

echo "== Node $NODE_VER"
fetch "https://nodejs.org/dist/v$NODE_VER/node-v$NODE_VER-win-x64.zip" "node-v$NODE_VER-win-x64.zip"
mkdir -p "$FILES/node"
unzip -q -j "$CACHE/node-v$NODE_VER-win-x64.zip" "node-v$NODE_VER-win-x64/node.exe" "node-v$NODE_VER-win-x64/LICENSE" -d "$FILES/node"

echo "== Engine"
mkdir -p "$FILES/engine/generator" "$FILES/engine/samples" "$FILES/engine/host-skill"
cp "$ROOT"/engine/*.py "$FILES/engine/"
cp "$ROOT"/engine/samples/*.json "$FILES/engine/samples/"
cp "$ROOT/engine/host-skill/SKILL.md" "$FILES/engine/host-skill/"
cp "$ROOT"/engine/generator/{generate.mjs,package.json,package-lock.json} "$FILES/engine/generator/"
(cd "$FILES/engine/generator" && npm ci --omit=dev --ignore-scripts --no-audit --no-fund --silent)

echo "== Director pages"
mkdir -p "$FILES/skills/deck-builder/scripts" "$FILES/skills/html-deck/pakco-html"
cp "$ROOT/skills/deck-builder/scripts/presentation_director.py" "$FILES/skills/deck-builder/scripts/"
cp -R "$ROOT/skills/html-deck/pakco-html/"{assets,templates,LICENSE} "$FILES/skills/html-deck/pakco-html/"

echo "== Notices and installer"
cp "$ROOT/LICENSE" "$FILES/LICENSE.txt"
python3 "$HERE/collect_notices.py" "$FILES" "$FILES/THIRD_PARTY_NOTICES.txt"
cp "$HERE/uninstall.ps1" "$FILES/"
cp "$HERE/install.ps1" "$HERE/Setup.cmd" "$HERE/Uninstall.cmd" "$STAGE/"
find "$STAGE" -name '__pycache__' -type d -prune -exec rm -rf {} +
find "$STAGE" -name '.DS_Store' -delete

ZIP="$OUT/$NAME.zip"
rm -f "$ZIP"
(cd "$OUT/stage" && zip -qr -X "$ZIP" "$NAME")
shasum -a 256 "$ZIP" | tee "$ZIP.sha256"
du -h "$ZIP"
