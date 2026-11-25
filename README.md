# Property Asset — Website

The public website for the Property Asset app: home page, support, Privacy Policy and Terms.
Published with GitHub Pages at <https://lynnsouz.github.io/PropertyAsset/>.

The App Store listing links here for its **Privacy Policy URL** (`privacy.html`) and **Support URL**
(`support.html`).

## Layout

```text
site.json            Name, description, URLs, support email, App Store link (empty until launch)
src/layout.html      Page shell: head, header, footer
src/*.html           Page bodies (index, support, 404)
content/i18n/*.json  All site text, one file per app language (en.json is the source; every key in every file)
content/legal/*.md   Privacy Policy and Terms, copied from the backend repo — don't edit here (English only)
assets/              Stylesheet, icons, app screenshots (light and dark, one folder per language)
build.py             Static site builder (Python standard library only) → _site/
scripts/sync.sh      Copies legal texts and screenshots from the sibling repos
```

## Working on it

```sh
python3 -I build.py --local && python3 -m http.server -d _site 8765   # preview at http://localhost:8765
```

Pushing to `main` builds and deploys (`.github/workflows/pages.yml`).

**Updating legal texts or screenshots.** Edit the legal texts in the backend repo
(`legal/*.md`, then `scripts/publish-legal.sh` so the app asks users to accept them), capture new
screenshots with `mise run screenshots` in the app repo (iPhone and iPad on iOS 27.2, in every
language), then here run `scripts/sync.sh`, commit and push. The website and the app then show the
same text, and each language's pages show the app in that language.

**At launch.** Set `support_email` and `app_store_url` in `site.json`; the support page and the
download button pick them up.
