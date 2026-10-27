#!/bin/bash
# Build .cpfont files the way the official CrossPoint font builder does (intervals reading,cjk-jp
# plus its Noto fallback fonts), optionally with the --smooth anti-aliasing of this repository.
#
# Usage:  scripts/build.sh <Regular.ttf> <name> <sizes> <outdir> [converter options...]
#   e.g.  BOLD_TTF=BIZUDMincho-Bold.ttf scripts/build.sh BIZUDMincho-Regular.ttf BIZ_UDMincho \
#           8,10,12,14,16,18 out --smooth
# Environment: BOLD_TTF=<Bold.ttf> adds a bold style; PYTHON=<python> (default python3).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
TTF="$1"; NAME="$2"; SIZES="$3"; OUT="$4"; shift 4
FB="${FALLBACK_DIR:-$HERE/../fallback-fonts}"
[ -d "$FB" ] || { echo "Run scripts/fetch_fallback_fonts.sh first" >&2; exit 1; }
ARGS=(--regular "$TTF")
[ -n "${BOLD_TTF:-}" ] && ARGS+=(--bold "$BOLD_TTF")
for f in NotoSans NotoSansHebrew NotoSansArmenian NotoSansGeorgian NotoSansEthiopic NotoSansCherokee \
         NotoSansTifinagh NotoSansCoptic NotoSansMath NotoSansSymbols NotoSansSymbols2 NotoEmoji; do
  ARGS+=(--default-fallback-font "$FB/$f-Regular.ttf")
done
ARGS+=(--default-fallback-font "$FB/NotoSansCJKjp-Regular.otf" --default-fallback-font "$FB/NotoSansCJKsc-Regular.otf")
mkdir -p "$OUT"
"${PYTHON:-python3}" "$HERE/fontconvert_sdcard.py" "${ARGS[@]}" \
  --name "$NAME" --intervals reading,cjk-jp --sizes "$SIZES" --output-dir "$OUT" "$@"
