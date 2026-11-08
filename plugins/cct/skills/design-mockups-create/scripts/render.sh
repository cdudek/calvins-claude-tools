#!/usr/bin/env bash
# Usage: bash scripts/render.sh <run-dir> [desktop|mobile|zoom150|both|all]
# Purpose: render every design HTML in a run folder to a high-resolution PNG, locally,
#          with headless Chromium. Nothing is uploaded and nothing needs a server.
# Output sections:
#   -#-#- RENDERED -#-#-   one line per PNG written
#   -#-#- SKIPPED -#-#-    files that produced no PNG, with the reason
#   -#-#- SUMMARY -#-#-    counts; exits non-zero if nothing rendered
#
# Viewports are 2x device pixel ratio via Playwright's "Desktop Chrome HiDPI" device, so a
# 1440-wide desktop shot lands at 2880 px. Full page, not just the fold: a design is judged
# whole.
set -euo pipefail

RUN="${1:?usage: render.sh <run-dir> [desktop|mobile|zoom150|both|all]}"
WHICH="${2:-both}"
[ -d "$RUN" ] || { echo "✗ no such run folder: $RUN" >&2; exit 1; }

RUNNER=""
if command -v playwright >/dev/null 2>&1; then
  RUNNER="playwright"
elif command -v npx >/dev/null 2>&1; then
  RUNNER="npx --yes playwright"
else
  echo "✗ Playwright is not installed. Install it once:" >&2
  echo "  pip install playwright && playwright install chromium" >&2
  exit 1
fi

shot() { # shot <html-file> <png-file> <viewport>
  $RUNNER screenshot \
    --device "Desktop Chrome HiDPI" \
    --viewport-size "$3" \
    --full-page \
    --wait-for-timeout 400 \
    "file://$1" "$2" >/dev/null 2>&1
}

echo "-#-#- RENDERED -#-#-"
ok=0
skipped=""
while IFS= read -r html; do
  dir=$(dirname "$html")
  base=$(basename "$html" .html)
  mkdir -p "$dir/shots"
  for vp in desktop mobile zoom150; do
    # both = desktop + mobile (as before); all = desktop + 150 % zoom, the Design stage's pair.
    case "$WHICH" in
      both) [ "$vp" = "zoom150" ] && continue ;;
      all) [ "$vp" = "mobile" ] && continue ;;
      *) [ "$WHICH" = "$vp" ] || continue ;;
    esac
    case "$vp" in
      mobile) size="390,844" ;;
      zoom150) size="960,600" ;;   # a 1440 x 900 window at 150 % zoom
      *) size="1440,900" ;;
    esac
    png="$dir/shots/${base}--${vp}@2x.png"
    if shot "$(cd "$dir" && pwd)/$(basename "$html")" "$png" "$size"; then
      echo "- $png ($(/usr/bin/file -b "$png" 2>/dev/null | cut -d, -f2 | tr -d ' '))"
      ok=$((ok + 1))
    else
      skipped="$skipped$html ($vp): Chromium returned an error"$'\n'
    fi
  done
done < <(find "$RUN" -type f -name "*.html" ! -name "gallery.html" | sort)

echo "-#-#- SKIPPED -#-#-"
[ -n "$skipped" ] && printf "%s" "$skipped" || echo "- none"

echo "-#-#- SUMMARY -#-#-"
echo "- run: $RUN"
echo "- png written: $ok"
[ "$ok" -gt 0 ] || { echo "- ✗ nothing rendered; is there any HTML under $RUN?" >&2; exit 1; }
