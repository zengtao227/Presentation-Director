#!/usr/bin/env bash
# Presentation Director — Bootstrap
# Installs all runtime dependencies and syncs skills to AI tool directories.
# Run once after cloning; re-run any time to update.
#
# Usage:
#   bash bootstrap.sh           # local setup only
#   bash bootstrap.sh --remote  # local setup + sync to remote SSH hosts

set -e
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── helpers ───────────────────────────────────────────────────────────────────
ok()   { printf "  ✓  %s\n" "$*"; }
info() { printf "  →  %s\n" "$*"; }
warn() { printf "  ⚠  %s\n" "$*"; }
fail() { printf "  ✗  %s\n" "$*" >&2; exit 1; }

# ── 1. Python version ─────────────────────────────────────────────────────────
echo ""
echo "Presentation Director bootstrap — source: $REPO"
echo ""
echo "1. Python"

PYTHON=$(command -v python3 || true)
if [ -z "$PYTHON" ]; then
  fail "python3 not found. Install Python 3.10+ and re-run."
fi
PY_VER=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$("$PYTHON" -c "import sys; print(sys.version_info.major)")
PY_MINOR=$("$PYTHON" -c "import sys; print(sys.version_info.minor)")
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
  fail "Python 3.10+ required (found $PY_VER)"
fi
ok "Python $PY_VER"

# ── 2. Python packages ────────────────────────────────────────────────────────
echo ""
echo "2. Python packages"

REQ="$REPO/requirements.txt"
if [ ! -f "$REQ" ]; then
  fail "requirements.txt not found at $REQ"
fi

# Try pip install; fall back to --break-system-packages on managed environments
if "$PYTHON" -m pip install -r "$REQ" -q 2>/dev/null; then
  ok "pip install (requirements.txt)"
elif "$PYTHON" -m pip install -r "$REQ" -q --break-system-packages 2>/dev/null; then
  ok "pip install --break-system-packages (requirements.txt)"
else
  # Last resort: user-level install
  "$PYTHON" -m pip install -r "$REQ" --user -q
  ok "pip install --user (requirements.txt)"
fi

# ── 3. Playwright browser binaries ───────────────────────────────────────────
echo ""
echo "3. Playwright browser (Chromium)"

if "$PYTHON" -m playwright install chromium 2>/dev/null; then
  ok "Chromium installed"
else
  warn "playwright install chromium failed — visual QA will fall back to static checks"
fi

# ── 4. Node.js / npm ─────────────────────────────────────────────────────────
echo ""
echo "4. Node.js dependencies (Marp CLI)"

if command -v npm &>/dev/null; then
  cd "$REPO" && npm install --silent
  ok "npm install (Marp CLI)"
else
  warn "npm not found — Marp PPTX export will be unavailable"
fi
cd "$REPO"

# ── 5. Skill sync ─────────────────────────────────────────────────────────────
echo ""
echo "5. Skill sync"

CLAUDE_SKILLS="$HOME/.claude/skills"
CODEX_SKILLS="$HOME/.codex/skills"

sync_skills() {
  local dest="$1"
  [ -d "$dest" ] || return 0
  rm -rf "$dest/deck-builder"
  cp -r "$REPO/skills/deck-builder" "$dest/"
  cp -r "$REPO/design-locks" "$dest/deck-builder/"
  rm -rf "$dest/ui-ux-pro-max"
  cp -r "$REPO/skills/ui-ux-pro-max" "$dest/"
  ok "$dest"
}

mkdir -p "$CLAUDE_SKILLS"
sync_skills "$CLAUDE_SKILLS"
sync_skills "$CODEX_SKILLS"

# Remote sync (optional)
if [[ "$1" == "--remote" ]]; then
  echo ""
  echo "6. Remote sync"
  REMOTE_HOSTS=(frank)
  for host in "${REMOTE_HOSTS[@]}"; do
    info "syncing to $host..."
    ssh "$host" "mkdir -p ~/.claude/skills ~/.codex/skills"
    rsync -a --delete \
      "$CLAUDE_SKILLS/deck-builder" \
      "$CLAUDE_SKILLS/ui-ux-pro-max" \
      "$host:~/.claude/skills/"
    ssh "$host" "[ -d ~/.codex/skills ] && echo yes || echo no" | grep -q yes && \
      rsync -a --delete \
        "$CLAUDE_SKILLS/deck-builder" \
        "$CLAUDE_SKILLS/ui-ux-pro-max" \
        "$host:~/.codex/skills/" || true
    ok "$host"
  done
fi

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "Bootstrap complete."
echo "Open a new Claude Code session for updated skills to take effect."
echo ""
