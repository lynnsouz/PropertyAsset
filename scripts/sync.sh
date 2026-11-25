#!/usr/bin/env bash
# Copies the source material from the sibling repositories into this one:
#   - legal texts:  ../Property Asset Backend/legal/{privacy,terms}.md  →  content/legal/
#   - screenshots:  ../Property Asset/build/screenshots/<lang>/*.png    →  assets/images/screenshots/<lang>/
#                   (capture them first with `mise run screenshots` in the app repo)
# Commit the result: GitHub Pages builds from this repository alone.
set -euo pipefail
cd "$(dirname "$0")/.."
BACKEND="${PA_BACKEND_DIR:-../Property Asset Backend}"
APP="${PA_APP_DIR:-../Property Asset}"

cp "$BACKEND/legal/privacy.md" "$BACKEND/legal/terms.md" content/legal/
echo "✓ Legal texts copied from $BACKEND/legal"

if compgen -G "$APP/build/screenshots/*/*.png" >/dev/null; then
  # One folder per language (en, pt-BR, de, …), named in lowercase like the site's language folders.
  # Only the screenshots the pages use: {{shot:NAME:…}}, {{ipad:NAME:…}}, {{mac:NAME:…}} in src/.
  used="$(grep -ohE '\{\{(shot|ipad|mac):[a-z0-9-]+' src/*.html | sed 's/.*://' | sort -u)"
  rm -rf assets/images/screenshots/*
  for dir in "$APP"/build/screenshots/*/; do
    lang="$(basename "$dir" | tr '[:upper:]' '[:lower:]')"
    mkdir -p "assets/images/screenshots/$lang"
    for png in "$dir"*.png; do
      name="$(basename "${png%.png}")"
      grep -qx "${name%-light}" <<<"$used" || grep -qx "${name%-dark}" <<<"$used" || continue
      # iPhone: 720 px wide JPEG, sharp on retina at the size the site shows it, ~100 KB each.
      # iPad (landscape): 1600 px wide, for the larger frame.
      size=1560; [[ "$name" == ipad-* ]] && size=1600
      sips -Z "$size" -s format jpeg -s formatOptions 80 "$png" --out "assets/images/screenshots/$lang/$name.jpg" >/dev/null
    done
  done
  echo "✓ Screenshots copied from $APP/build/screenshots ($(ls assets/images/screenshots | tr '\n' ' '))"
else
  echo "• No screenshots in $APP/build/screenshots (run: mise run screenshots in the app repo)"
fi
