#!/usr/bin/env bash
# MD2PPT Global Skill Installer
# Run from the MD2PPT repo root after any update to skills or design-locks.
#
# Usage:
#   bash install.sh           # local only
#   bash install.sh --remote  # local + sync to remote SSH hosts

set -e

MD2PPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_SKILLS="$HOME/.claude/skills"
CODEX_SKILLS="$HOME/.codex/skills"

# Remote SSH hosts to sync when --remote is passed
REMOTE_HOSTS=(frank)

install_local() {
  local dest="$1"
  if [ ! -d "$dest" ]; then
    echo "  ⚠️  $dest does not exist — skipping"
    return
  fi
  rm -rf "$dest/deck-builder"
  cp -r "$MD2PPT/skills/deck-builder" "$dest/"
  cp -r "$MD2PPT/design-locks" "$dest/deck-builder/"
  # ui-ux-pro-max is never installed from here: deck-builder uses the global official skill,
  # and this repo keeps no copy of it (an old bundled copy used to overwrite the global one).
  # presentation_director.py resolves pakco-html as <skills>/html-deck/pakco-html.
  rm -rf "$dest/html-deck"
  cp -r "$MD2PPT/skills/html-deck" "$dest/"
  echo "  ✓  $dest"
}

install_remote() {
  local host="$1"
  echo "  syncing to $host..."
  ssh "$host" "mkdir -p ~/.claude/skills ~/.codex/skills"
  rsync -a --delete \
    "$CLAUDE_SKILLS/deck-builder" \
    "$CLAUDE_SKILLS/html-deck" \
    "$host:~/.claude/skills/"
  # sync to codex on remote only if the dir already exists
  ssh "$host" "[ -d ~/.codex/skills ] && echo yes || echo no" | grep -q yes && \
    rsync -a --delete \
      "$CLAUDE_SKILLS/deck-builder" \
      "$CLAUDE_SKILLS/html-deck" \
      "$host:~/.codex/skills/" || true
  echo "  ✓  $host"
}

echo "MD2PPT skill installer — source: $MD2PPT"
echo ""

echo "Local:"
mkdir -p "$CLAUDE_SKILLS"
install_local "$CLAUDE_SKILLS"
install_local "$CODEX_SKILLS"

if [[ "$1" == "--remote" ]]; then
  echo ""
  echo "Remote:"
  for host in "${REMOTE_HOSTS[@]}"; do
    install_remote "$host"
  done
fi

echo ""
echo "Done. Open a new Claude Code session for updated skills to take effect."
