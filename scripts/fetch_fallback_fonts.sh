#!/bin/bash
# Download the Noto fallback fonts that the official CrossPoint font builder uses, and verify them.
# The fonts are not stored in this repository (they are SIL OFL 1.1 fonts; see NOTICE.md).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="${1:-$HERE/../fallback-fonts}"
BASE=https://raw.githubusercontent.com/crosspoint-reader/crosspoint-tools/master/scripts/font-builder/default-fallback-fonts
mkdir -p "$DEST"
while read -r sum name; do
  [ -f "$DEST/$name" ] || curl -sSfL -o "$DEST/$name" "$BASE/$name"
  echo "$sum  $DEST/$name" | shasum -a 256 -c -
done < "$HERE/fallback-fonts.sha256"
