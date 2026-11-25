#!/usr/bin/env python3
"""Builds the Property Asset website into _site/. Standard library only.

    python3 -I build.py                 # for GitHub Pages (paths under site.json's base_path)
    python3 -I build.py --local         # for previewing: python3 -m http.server -d _site

Pages: src/index.html, src/support.html and src/404.html are wrapped in src/layout.html;
content/legal/*.md (synced from the backend repo by scripts/sync.sh) become privacy.html and terms.html.
Every page is built in each of the app's languages: English at the root, the others in /<code>/
(e.g. /pt-br/support.html), with a language menu in the header. The legal texts stay in English.

Text lives in content/i18n/<lang>.json; en.json is the source, and every language needs every key.
Placeholders in pages: {{t:<key>}} (translated text), {{home}} (this language's root), {{base}}
(the site root, for assets), {{app_store_button}}, {{contact}}, and {{shot:<name>:<alt key>}} for a
screenshot in assets/images/screenshots/<lang>/<name>-light.jpg / -dark.jpg (iPhone frame), captured
in the page's language. {{ipad:…}} and
{{mac:…}} take the same arguments for a landscape iPad capture, in an iPad frame or a Mac window.
"""
import datetime
import html
import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "_site"


# MARK: - Markdown (the subset the legal texts use)

def inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)

    def link(match: re.Match) -> str:
        label, url = match.group(1), match.group(2)
        if not re.match(r"^(https?://|mailto:|#|[\w-]+\.html)", url):
            return match.group(0)  # "[PLACEHOLDER](…)" that isn't a URL stays as written
        return f'<a href="{html.escape(url)}">{label}</a>'

    return re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, text)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", re.sub(r"<[^>]+>", "", text).lower()).strip("-")


BLOCK_START = re.compile(r"^(#{1,4} |>|\||\s*[-*] |-{3,}\s*$)")


def markdown(source: str) -> str:
    lines, out, i = source.splitlines(), [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif heading := re.match(r"^(#{1,4}) (.+)$", line):
            level, text = len(heading.group(1)), inline(heading.group(2).strip())
            out.append(f'<h{level} id="{slug(text)}">{text}</h{level}>')
            i += 1
        elif re.match(r"^-{3,}\s*$", line):
            out.append("<hr>")
            i += 1
        elif line.startswith(">"):
            quoted = []
            while i < len(lines) and lines[i].startswith(">"):
                quoted.append(lines[i].lstrip(">").strip())
                i += 1
            out.append(f"<blockquote>{markdown(chr(10).join(quoted))}</blockquote>")
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.match(r"^:?-+:?$", c) for c in cells):
                    rows.append(cells)
                i += 1
            head = "".join(f'<th scope="col">{inline(c)}</th>' for c in rows[0])
            body = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>" for row in rows[1:])
            out.append(f'<div class="table"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')
        elif re.match(r"^\s*[-*] ", line):
            block = []
            while i < len(lines) and (re.match(r"^\s*[-*] ", lines[i]) or lines[i].startswith("  ")):
                block.append(lines[i])
                i += 1
            out.append(bullets(block))
        else:
            paragraph = []
            while i < len(lines) and lines[i].strip() and not BLOCK_START.match(lines[i]):
                paragraph.append(lines[i].strip())
                i += 1
            out.append(f"<p>{inline(' '.join(paragraph))}</p>")
    return "\n".join(out)


def bullets(block: list[str]) -> str:
    items: list[list[str]] = []
    for line in block:
        if re.match(r"^[-*] ", line):
            items.append([line[2:].strip()])
        else:
            items[-1].append(line[2:])
    return "<ul>" + "".join(f"<li>{inline(first)}{bullets(rest) if rest else ''}</li>" for first, *rest in items) + "</ul>"


# MARK: - Languages

# The app's languages. English is at the site root; the others in a folder named after the code.
LANGUAGES = ["en", "pt-BR", "es", "fr", "de", "it", "sv", "da", "nb", "fi", "ar", "zh-Hans", "hi", "bn", "id", "ja", "ru"]
# Written right to left: the page gets dir="rtl" and the stylesheet uses logical (start/end) properties.
RTL = {"ar"}
GLOBE = ('<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" '
         'stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18"/>'
         '<path d="M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9s1.3-6.4 3.8-9z"/></svg>')


def folder(lang: str) -> str:
    return "" if lang == "en" else lang.lower() + "/"


def load_strings() -> dict[str, dict[str, str]]:
    """Every language must have every English key, with the same HTML tags and placeholders."""
    strings = {lang: json.loads((ROOT / "content" / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))
               for lang in LANGUAGES}
    english = strings["en"]
    shape = lambda text: sorted(re.findall(r"</?\w+|\{\{\w+\}\}", text))
    for lang, table in strings.items():
        missing = set(english) - set(table)
        assert not missing, f"{lang}.json is missing {sorted(missing)}"
        for key, text in english.items():
            assert shape(text) == shape(table[key]), f"{lang}.json {key}: tags differ from English"
    return strings


# MARK: - Pages

def shots(base: str, lang: str, name: str) -> str:
    """This language's screenshot folder (the app captured in that language); fails if a capture is missing."""
    folder = f"assets/images/screenshots/{lang.lower()}"
    for appearance in ("light", "dark"):
        assert (ROOT / folder / f"{name}-{appearance}.jpg").exists(), f"missing {folder}/{name}-{appearance}.jpg (scripts/sync.sh)"
    return base + folder


def screenshot(base: str, lang: str, name: str, alt: str) -> str:
    path = shots(base, lang, name)
    return (
        f'<div class="phone"><picture>'
        f'<source srcset="{path}/{name}-dark.jpg" media="(prefers-color-scheme: dark)">'
        f'<img src="{path}/{name}-light.jpg" alt="{html.escape(alt)}" width="719" height="1560" loading="lazy">'
        f"</picture></div>"
    )


def picture(base: str, lang: str, name: str, alt: str, width: int, height: int) -> str:
    path = shots(base, lang, name)
    return (
        f'<picture><source srcset="{path}/{name}-dark.jpg" media="(prefers-color-scheme: dark)">'
        f'<img src="{path}/{name}-light.jpg" alt="{html.escape(alt)}" width="{width}" height="{height}" loading="lazy">'
        f"</picture>"
    )


def ipad(base: str, lang: str, name: str, alt: str) -> str:
    return f'<div class="ipad">{picture(base, lang, name, alt, 1600, 1103)}</div>'


def mac(base: str, lang: str, name: str, alt: str) -> str:
    """A Mac window around an iPad capture; the Mac shows the app without the iPad status bar, so it's cropped."""
    return (
        '<div class="mac"><div class="mac-bar" aria-hidden="true"><i></i><i></i><i></i><span>Property Asset</span></div>'
        f'<div class="mac-screen">{picture(base, lang, name, alt, 1600, 1103)}</div></div>'
    )


def fill(template: str, config: dict, base: str, lang: str, t: dict[str, str]) -> str:
    if config["app_store_url"]:
        button = f'<a class="button" href="{html.escape(config["app_store_url"])}">{t["app_store_download"]}</a>'
    else:
        button = f'<span class="button disabled" aria-disabled="true">{t["app_store_soon"]}</span>'
    if config["support_email"]:
        email = html.escape(config["support_email"])
        contact = (f'<div class="contact"><p><strong>{t["contact_email"]}</strong> <a href="mailto:{email}">{email}</a></p>'
                   f'<p>{t["contact_reply"]}</p></div>')
    else:
        contact = f'<div class="contact"><p>{t["contact_soon"]}</p></div>'
    template = re.sub(r"\{\{shot:([\w-]+):(\w+)\}\}", lambda m: screenshot(base, lang, m.group(1), t[m.group(2)]), template)
    template = re.sub(r"\{\{ipad:([\w-]+):(\w+)\}\}", lambda m: ipad(base, lang, m.group(1), t[m.group(2)]), template)
    template = re.sub(r"\{\{mac:([\w-]+):(\w+)\}\}", lambda m: mac(base, lang, m.group(1), t[m.group(2)]), template)
    return template.replace("{{app_store_button}}", button).replace("{{contact}}", contact)


def language_menu(base: str, lang: str, file: str, strings: dict) -> str:
    """A disclosure menu (works without JavaScript) linking to this page in every language."""
    target = "" if file in ("index.html", "404.html") else file
    items = []
    for other in sorted(LANGUAGES, key=lambda code: strings[code]["language_name"].casefold()):
        current = ' aria-current="true"' if other == lang else ""
        items.append(f'<li><a href="{base}{folder(other)}{target}" lang="{other}" hreflang="{other}"{current}>'
                     f'{strings[other]["language_name"]}</a></li>')
    label = html.escape(strings[lang]["language_menu"])
    return (f'<details class="lang-menu"><summary aria-label="{label}: {strings[lang]["language_name"]}">{GLOBE}'
            f'<span class="lang-code">{lang.split("-")[0].upper()}</span></summary>'
            f'<ul aria-label="{label}">{"".join(items)}</ul></details>')


def navigation(home: str, current: str, t: dict[str, str]) -> str:
    links = [("", "#features", t["nav_features"], "optional"), ("support.html", "support.html", t["nav_support"], ""),
             ("privacy.html", "privacy.html", t["nav_privacy"], "")]
    parts = []
    for page, href, label, css in links:
        attributes = f' class="{css}"' if css else ""
        if page and page == current:
            attributes += ' aria-current="page"'
        parts.append(f'<a href="{home}{href}"{attributes}>{label}</a>')
    return "".join(parts)


def legal_body(kind: str, t: dict[str, str]) -> str:
    source = (ROOT / "content" / "legal" / f"{kind}.md").read_text(encoding="utf-8")
    body = re.sub(r"(<h1[^>]*>)Property Asset — ", r"\1", markdown(source), count=1)
    sections = re.findall(r'<h2 id="([^"]+)">(.+?)</h2>', body)
    toc = ""
    if len(sections) > 4:
        items = "".join(f'<li><a href="#{anchor}">{re.sub(r"^[0-9.]+ ", "", title)}</a></li>' for anchor, title in sections)
        toc = f'<nav class="toc" aria-label="Contents" lang="en"><strong>Contents</strong><ol>{items}</ol></nav>'
    body = re.sub(r"(</h1>)", r"\1" + toc.replace("\\", "\\\\"), body, count=1) if toc else body
    # The legal texts are English until translated versions are reviewed.
    notice = f'<p class="notice">{t["legal_english_only"]}</p>' if t["legal_english_only"] else ""
    return f'<section class="page legal"><div class="wrap narrow">{notice}<div lang="en">{body}</div></div></section>'


def main() -> None:
    config = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
    base = "/" if "--local" in sys.argv else config["base_path"]
    layout = (ROOT / "src" / "layout.html").read_text(encoding="utf-8")
    strings = load_strings()

    sources: dict[str, tuple[str, str]] = {}  # file → (title key, body template)
    for name in ("index", "support", "404"):
        source = (ROOT / "src" / f"{name}.html").read_text(encoding="utf-8")
        title = re.match(r"<!-- title: (\w+) -->", source).group(1)
        sources[f"{name}.html"] = (title, source.split("-->", 1)[1])
    for kind in ("privacy", "terms"):
        sources[f"{kind}.html"] = (f"legal_{kind}_title", "")

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "assets", OUT / "assets")
    written = []
    for lang in LANGUAGES:
        t, home = strings[lang], base + folder(lang)
        for file, (title_key, body) in sources.items():
            if file == "404.html" and lang != "en":
                continue  # GitHub Pages only serves the root 404 page
            if not body:
                body = legal_body(file.removesuffix(".html"), t)
            title = t[title_key] if file == "index.html" else f"{t[title_key]} · Property Asset"
            path = "" if file == "index.html" else file
            alternates = "\n".join(
                f'<link rel="alternate" hreflang="{other}" href="{config["base_url"]}{folder(other)}{path}">'
                for other in LANGUAGES) + f'\n<link rel="alternate" hreflang="x-default" href="{config["base_url"]}{path}">'
            page = (layout.replace("{{body}}", fill(body.strip(), config, base, lang, t))
                    .replace("{{nav}}", navigation(home, file, t) + language_menu(base, lang, file, strings))
                    .replace("{{alternates}}", "" if file == "404.html" else alternates)
                    .replace("{{title}}", html.escape(re.sub(r"&nbsp;", " ", title)))
                    .replace("{{description}}", html.escape(t["meta_description"]))
                    .replace("{{canonical}}", config["base_url"] + folder(lang) + path)
                    .replace("{{base_url}}", config["base_url"])
                    .replace("{{page_class}}", file.removesuffix(".html"))
                    .replace("{{lang}}", lang)
                    .replace("{{dir}}", "rtl" if lang in RTL else "ltr")
                    .replace("{{year}}", str(datetime.date.today().year)))
            page = re.sub(r"\{\{t:(\w+)\}\}", lambda m: t[m.group(1)], page)
            page = page.replace("{{home}}", home).replace("{{base}}", base)
            assert "{{" not in page, f"{lang}/{file}: unreplaced placeholder {re.search(r'{{[^}]*}}', page).group(0)}"
            target = OUT / folder(lang) / file
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(page, encoding="utf-8")
            if file != "404.html":
                written.append(folder(lang) + path)

    urls = "".join(f"<url><loc>{config['base_url']}{path}</loc></url>" for path in written)
    (OUT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {config['base_url']}sitemap.xml\n")
    print(f"Built {OUT.name}/: {len(written) + 1} pages in {len(LANGUAGES)} languages (base {base})")


if __name__ == "__main__":
    main()
