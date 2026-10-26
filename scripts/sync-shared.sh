#!/usr/bin/env bash
# Copy shared/ into every skill so each skill folder installs standalone.
# Usage: scripts/sync-shared.sh          # write copies
#        scripts/sync-shared.sh --check  # fail if any copy has drifted (CI)
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
check=false
[[ "${1:-}" == "--check" ]] && check=true
drift=0

for skill in "$root"/skills/*/; do
  for kind in scripts references; do
    src_dir="$root/shared/$kind"
    [[ -d "$src_dir" ]] || continue
    for src in "$src_dir"/*; do
      [[ -f "$src" ]] || continue
      dest="$skill$kind/$(basename "$src")"
      if $check; then
        if ! cmp -s "$src" "$dest"; then
          echo "drift: ${dest#$root/}"
          drift=1
        fi
      else
        mkdir -p "$skill$kind"
        cp "$src" "$dest"
      fi
    done
  done
done

if $check; then
  [[ $drift -eq 0 ]] && echo "shared files in sync" || exit 1
else
  chmod +x "$root"/skills/*/scripts/*.py 2>/dev/null || true
  echo "synced shared/ into $(ls -d "$root"/skills/*/ | wc -l) skills"
fi
