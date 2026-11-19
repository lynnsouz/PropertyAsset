#!/usr/bin/env python3
"""Builds the Property Asset website into _site/. Standard library only.

    python3 -I build.py                 # for GitHub Pages (paths under site.json's base_path)
    python3 -I build.py --local         # for previewing: python3 -m http.server -d _site

Pages: src/index.html, src/support.html and src/404.html are wrapped in src/layout.html;
content/legal/*.md (synced from the backend repo by scripts/sync.sh) become privacy.html and terms.html.

Placeholders in pages: {{base}}, {{app_store_button}}, {{contact}}, and {{shot:<name>:<alt text>}}
for a screenshot in assets/images/screenshots/<name>-light.jpg / -dark.jpg.
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
LEGAL = {"privacy": "Privacy Policy", "terms": "Terms and Conditions"}


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


# MARK: - Pages

def screenshot(base: str, name: str, alt: str) -> str:
    folder = f"{base}assets/images/screenshots"
    return (
        f'<div class="phone"><picture>'
        f'<source srcset="{folder}/{name}-dark.jpg" media="(prefers-color-scheme: dark)">'
        f'<img src="{folder}/{name}-light.jpg" alt="{html.escape(alt)}" width="719" height="1560" loading="lazy">'
        f"</picture></div>"
    )


def fill(template: str, config: dict, base: str) -> str:
    if config["app_store_url"]:
        button = f'<a class="button" href="{html.escape(config["app_store_url"])}">Download on the App Store</a>'
    else:
        button = '<span class="button disabled" aria-disabled="true">Coming soon to the App Store</span>'
    if config["support_email"]:
        email = html.escape(config["support_email"])
        contact = (f'<div class="contact"><p><strong>Email:</strong> <a href="mailto:{email}">{email}</a></p>'
                   "<p>We reply within two business days. Please include your app version (Workspace tab, at the bottom).</p></div>")
    else:
        contact = '<div class="contact"><p>A support email address will be listed here when the app launches.</p></div>'
    template = re.sub(r"\{\{shot:([\w-]+):([^}]+)\}\}", lambda m: screenshot(base, m.group(1), m.group(2)), template)
    return template.replace("{{base}}", base).replace("{{app_store_button}}", button).replace("{{contact}}", contact)


def navigation(base: str, current: str) -> str:
    links = [("", "#features", "Features", "optional"), ("support.html", "support.html", "Support", ""),
             ("privacy.html", "privacy.html", "Privacy", "")]
    parts = []
    for page, href, label, css in links:
        attributes = f' class="{css}"' if css else ""
        if page and page == current:
            attributes += ' aria-current="page"'
        parts.append(f'<a href="{base}{href}"{attributes}>{label}</a>')
    return "".join(parts)


def legal_body(kind: str) -> str:
    source = (ROOT / "content" / "legal" / f"{kind}.md").read_text(encoding="utf-8")
    body = re.sub(r"(<h1[^>]*>)Property Asset — ", r"\1", markdown(source), count=1)
    sections = re.findall(r'<h2 id="([^"]+)">(.+?)</h2>', body)
    toc = ""
    if len(sections) > 4:
        items = "".join(f'<li><a href="#{anchor}">{re.sub(r"^[0-9.]+ ", "", title)}</a></li>' for anchor, title in sections)
        toc = f'<nav class="toc" aria-label="Contents"><strong>Contents</strong><ol>{items}</ol></nav>'
    body = re.sub(r"(</h1>)", r"\1" + toc.replace("\\", "\\\\"), body, count=1) if toc else body
    return f'<section class="page legal"><div class="wrap narrow">{body}</div></section>'


def main() -> None:
    config = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
    base = "/" if "--local" in sys.argv else config["base_path"]
    layout = (ROOT / "src" / "layout.html").read_text(encoding="utf-8")

    pages: dict[str, tuple[str, str]] = {}  # output file → (title, body)
    for name in ("index", "support", "404"):
        source = (ROOT / "src" / f"{name}.html").read_text(encoding="utf-8")
        title = re.match(r"<!-- title: (.+?) -->", source).group(1)
        pages[f"{name}.html"] = (title, source.split("-->", 1)[1])
    for kind, title in LEGAL.items():
        pages[f"{kind}.html"] = (f"{title} · Property Asset", legal_body(kind))

    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "assets", OUT / "assets")
    for file, (title, body) in pages.items():
        canonical = config["base_url"] + ("" if file == "index.html" else file)
        page = (layout.replace("{{body}}", fill(body.strip(), config, base))
                .replace("{{nav}}", navigation(base, file))
                .replace("{{title}}", html.escape(title))
                .replace("{{description}}", html.escape(config["description"]))
                .replace("{{canonical}}", canonical)
                .replace("{{base_url}}", config["base_url"])
                .replace("{{page_class}}", file.removesuffix(".html"))
                .replace("{{year}}", str(datetime.date.today().year)))
        page = page.replace("{{base}}", base)
        assert "{{" not in page, f"{file}: unreplaced placeholder"
        (OUT / file).write_text(page, encoding="utf-8")

    urls = "".join(f"<url><loc>{config['base_url']}{'' if f == 'index.html' else f}</loc></url>"
                   for f in pages if f != "404.html")
    (OUT / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {config['base_url']}sitemap.xml\n")
    print(f"Built {OUT.name}/: {', '.join(pages)} (base {base})")


if __name__ == "__main__":
    main()
