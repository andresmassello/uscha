#!/usr/bin/env python3
"""Render docs/field-notes/*.md into site pages (site/field-notes/<slug>/index.html + ES twin).

The .md in docs/ is the canonical source; these pages are BUILD OUTPUT (run by sync-docs.sh).
Minimal, dependency-free Markdown: h1/h2, paragraphs, **bold**, *em*, `code`, bullet lists,
[links](url). Anything fancier is deliberately unsupported -- keep the notes simple.
"""
import io, os, re, sys, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "docs", "field-notes")
OUT = os.path.join(ROOT, "site")

INLINE = [
    (re.compile(r"`([^`]+)`"), lambda m: "<code>" + html.escape(m.group(1)) + "</code>"),
    (re.compile(r"\*\*(.+?)\*\*"), lambda m: "<strong>" + m.group(1) + "</strong>"),
    (re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])"), lambda m: "<em>" + m.group(1) + "</em>"),
    (re.compile(r"\[([^\]]+)\]\(([^)]+)\)"), lambda m: '<a href="' + html.escape(m.group(2), quote=True) + '">' + m.group(1) + "</a>"),
]

def inline(s):
    # escape first, then re-introduce markup (code content was escaped inside its own handler,
    # so escape everything except backtick spans)
    parts = re.split(r"(`[^`]+`)", s)
    out = []
    for p in parts:
        if p.startswith("`") and p.endswith("`") and len(p) > 1:
            out.append("<code>" + html.escape(p[1:-1]) + "</code>")
        else:
            e = html.escape(p, quote=False)
            for rx, fn in INLINE[1:]:
                e = rx.sub(fn, e)
            out.append(e)
    return "".join(out)

def render(md):
    lines = md.splitlines()
    body, title = [], None
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("# "):
            title = ln[2:].strip(); i += 1; continue
        if ln.startswith("## "):
            body.append("<h2>" + inline(ln[3:].strip()) + "</h2>"); i += 1; continue
        if ln.strip().startswith(("- ", "* ")):
            items = []
            while i < len(lines) and lines[i].strip().startswith(("- ", "* ")):
                items.append("<li>" + inline(lines[i].strip()[2:]) + "</li>"); i += 1
            body.append("<ul>" + "".join(items) + "</ul>"); continue
        if not ln.strip():
            i += 1; continue
        para = [ln]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].startswith("#") and not lines[i].strip().startswith(("- ", "* ")):
            para.append(lines[i]); i += 1
        body.append("<p>" + inline(" ".join(x.strip() for x in para)) + "</p>")
    return title or "Field note", "\n".join(body)

PAGE = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — uscha</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="https://uscha.dev/{canon}">
<link rel="alternate" hreflang="en" href="https://uscha.dev/{en_url}">
<link rel="alternate" hreflang="es" href="https://uscha.dev/{es_url}">
<link rel="alternate" hreflang="x-default" href="https://uscha.dev/{en_url}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Chivo:wght@600;700;800;900&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{css}">
<style>.article ul{{margin-top:14px;padding-left:22px;color:var(--fg-soft)}} .article li{{margin:6px 0}} .article h2{{margin-top:44px}}</style>
</head>
<body>
<header class="bar">
  <div class="bar-in">
    <a class="wordmark" href="{home}">uscha<b>.</b>dev</a>
    <nav>
      <a href="{home}#{lib_anchor}">{lib_label}</a>
      <a href="{how}">{how_label}</a>
      <a href="https://github.com/andresmassello/uscha">github</a>
      <a class="lang" href="{twin}">{twin_label}</a>
    </nav>
  </div>
</header>
<main>
  <article class="article">
    <div class="kicker">{kicker}</div>
    <h1>{title}</h1>
{body}
    <p style="margin-top:32px;color:var(--mute);font-size:13px">{source_note} <a href="https://github.com/andresmassello/uscha/blob/main/docs/field-notes/{src_name}">docs/field-notes/{src_name}</a>.</p>
    <div class="backlinks">
      <a href="{diamond}">{diamond_label}</a>
      <a href="{home}">{back_label}</a>
    </div>
  </article>
</main>
<footer>
  <div class="wrap">
    <p class="foot-motto">{motto}</p>
    <div class="foot-links">
      <a href="https://github.com/andresmassello/uscha">github.com/andresmassello/uscha</a>
      <a href="https://www.npmjs.com/package/@andresmassello/uscha">npm · @andresmassello/uscha</a>
      <a href="mailto:info@uscha.dev">info@uscha.dev</a>
    </div>
    <p class="foot-fine">© 2026 Andres Massello · {lic} · uscha-kit v{version}</p>
  </div>
</footer>
</body>
</html>
"""

def version():
    return io.open(os.path.join(ROOT, "uscha-kit", "VERSION"), encoding="utf-8").read().split()[-1]

def build_one(slug, en_md, es_md):
    ver = version()
    for lang, src_name, md in (("en", en_md, io.open(os.path.join(SRC, en_md), encoding="utf-8").read()),
                               ("es", es_md, io.open(os.path.join(SRC, es_md), encoding="utf-8").read())):
        title, body = render(md)
        first_p = re.search(r"<p>(.*?)</p>", body, re.S)
        desc = html.escape(re.sub(r"<[^>]+>", "", first_p.group(1))[:200] if first_p else title, quote=True)
        en_url, es_url = f"field-notes/{slug}", f"es/field-notes/{slug}"
        if lang == "en":
            out = os.path.join(OUT, "field-notes", slug, "index.html")
            ctx = dict(css="../../assets/uscha.css", home="../../index.html", how="../../how/index.html",
                       diamond="../../diamond/index.html", twin=f"../../es/field-notes/{slug}/index.html",
                       twin_label="ES", canon=en_url, lib_anchor="library", lib_label="library",
                       how_label="how it works", kicker="field note · real project, anonymized",
                       diamond_label="The thesis: the diamond →", back_label="← Back to home",
                       motto="The agent executes · the method governs · evidence decides · the human approves.",
                       lic="MIT License", source_note="Canonical source, kept in the repo:")
        else:
            out = os.path.join(OUT, "es", "field-notes", slug, "index.html")
            ctx = dict(css="../../../assets/uscha.css", home="../../index.html", how="../../how/index.html",
                       diamond="../../diamond/index.html", twin=f"../../../field-notes/{slug}/index.html",
                       twin_label="EN", canon=es_url, lib_anchor="biblioteca", lib_label="biblioteca",
                       how_label="cómo funciona", kicker="nota de campo · proyecto real, anonimizado",
                       diamond_label="La tesis: el diamante →", back_label="← Volver al inicio",
                       motto="El agente ejecuta · el método gobierna · la evidencia decide · el humano aprueba.",
                       lic="Licencia MIT", source_note="Fuente canónica, en el repo:")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        io.open(out, "w", encoding="utf-8", newline="\n").write(PAGE.format(
            lang=lang, title=html.escape(title), desc=desc, en_url=en_url, es_url=es_url,
            body=body, src_name=src_name, version=ver, **ctx))
        print("wrote", os.path.relpath(out, ROOT))

if __name__ == "__main__":
    build_one("001-treasury-migration",
              "FIELD-NOTE-001-treasury-migration.md",
              "FIELD-NOTE-001-treasury-migration-ES.md")
