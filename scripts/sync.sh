#!/usr/bin/env bash
# Copies the source material from the sibling repositories into this one:
#   - legal texts:  ../Property Asset Backend/legal/{privacy,terms}.md  →  content/legal/
#   - screenshots:  ../Property Asset/build/screenshots/*.png           →  assets/images/screenshots/
#                   (capture them first with `mise run screenshots` in the app repo)
# Commit the result: GitHub Pages builds from this repository alone.
set -euo pipefail
cd "$(dirname "$0")/.."
BACKEND="${PA_BACKEND_DIR:-../Property Asset Backend}"
APP="${PA_APP_DIR:-../Property Asset}"

cp "$BACKEND/legal/privacy.md" "$BACKEND/legal/terms.md" content/legal/
echo "✓ Legal texts copied from $BACKEND/legal"

if compgen -G "$APP/build/screenshots/*.png" >/dev/null; then
  rm -f assets/images/screenshots/*
  for png in "$APP"/build/screenshots/*.png; do
    name="$(basename "${png%.png}")"
    # iPhone: 720 px wide JPEG, sharp on retina at the size the site shows it, ~100 KB each.
    # iPad (landscape): 1600 px wide, for the larger frame.
    size=1560; [[ "$name" == ipad-* ]] && size=1600
    sips -Z "$size" -s format jpeg -s formatOptions 80 "$png" --out "assets/images/screenshots/$name.jpg" >/dev/null
  done
  echo "✓ Screenshots copied from $APP/build/screenshots"
else
  echo "• No screenshots in $APP/build/screenshots (run: mise run screenshots in the app repo)"
fi
