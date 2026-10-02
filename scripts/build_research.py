#!/usr/bin/env python3
# Builds the THOR-SEC research record from scripts/research.json.
#
# Outputs (plain static files, committed to the repository):
#   research/<id>.html            one page per paper, with citation metadata
#   index.html                    the "Latest research" list (between build markers)
#   research.html                 the "Papers" list (between build markers)
#   feed.xml, sitemap.xml         rewritten in full
#
# Rule: build tools may write static files; nothing they write runs in the browser.
# Usage: python3 scripts/build_research.py          write outputs
#        python3 scripts/build_research.py --check  fail if any output is out of date

from __future__ import annotations

from html import escape
from pathlib import Path
import json
import re
import sys
import textwrap

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "scripts/research.json").read_text(encoding="utf-8"))
SITE = DATA["site"]
BASE = SITE["base"]
ENTRIES = DATA["entries"]
PAPERS = [e for e in ENTRIES if e["kind"] == "paper"]
CASE_DATA_PATH = ROOT / "scripts/case_studies.json"
CASE_DATA = json.loads(CASE_DATA_PATH.read_text(encoding="utf-8")) if CASE_DATA_PATH.exists() else {"entries": []}
CASE_STUDIES = CASE_DATA["entries"]
LATEST_KINDS = ("paper", "tool", "lab")
LATEST_COUNT = 3
SOCIAL_IMAGE = BASE + "assets/thor-sec-social-card.png"
SOCIAL_ALT = "THOR-SEC: independent security research by Thor Thor"


def h(text: str) -> str:
    # Attributes are always double-quoted, so apostrophes can stay readable.
    return escape(text, quote=False).replace('"', "&quot;")


def paper_path(entry: dict) -> str:
    return f"research/{entry['id']}.html"


def doi_url(entry: dict) -> str:
    return f"https://doi.org/{entry['doi']}"


def plain_citation(e: dict) -> str:
    year = e["date"][:4]
    text = f"{SITE['author_citation'].split(',')[0]}, T. ({year}). {e['full_title']} ({e['version']}). {e['publisher']}. {doi_url(e)}"
    return "\n".join(textwrap.wrap(text, 78))


def bibtex(e: dict) -> str:
    key = f"{SITE['author_citation'].split(',')[0].lower()}{e['date'][:4]}{e['id']}"
    return "\n".join([
        f"@misc{{{key},",
        f"  author    = {{{SITE['author_citation']}}},",
        f"  title     = {{{e['full_title']}}},",
        f"  year      = {{{e['date'][:4]}}},",
        f"  version   = {{{e['version']}}},",
        f"  publisher = {{{e['publisher']}}},",
        f"  doi       = {{{e['doi']}}},",
        f"  url       = {{{doi_url(e)}}}",
        "}",
    ])


def replace_block(text: str, name: str, body: str, path: str) -> str:
    start = f"<!-- build:{name}:start -->"
    end = f"<!-- build:{name}:end -->"
    pattern = re.compile(re.escape(start) + r".*?" + r"([ \t]*)" + re.escape(end), re.S)
    match = pattern.search(text)
    if not match:
        raise SystemExit(f"{path}: build markers for '{name}' not found")
    indent = match.group(1)
    return text[:match.start()] + start + "\n" + body + indent + end + text[match.end():]


# ------------------------------------------------------------------ home page

def latest_block() -> str:
    items = sorted((e for e in ENTRIES if e["kind"] in LATEST_KINDS), key=lambda e: e["date"], reverse=True)[:LATEST_COUNT]
    out = []
    for e in items:
        out.append('          <li class="entry">')
        if e["kind"] == "paper":
            out.append(f'            <p class="entry-meta"><time datetime="{e["date"]}">{e["date"]}</time> &middot; <span class="tag">paper</span> &middot; DOI {h(e["doi"])}</p>')
            out.append(f'            <h3><a href="./{paper_path(e)}">{h(e["title"])}</a></h3>')
            out.append(f'            <p>{h(e["home_summary"])}</p>')
            out.append('            <ul class="inline-links">')
            out.append(f'              <li><a href="{doi_url(e)}">DOI</a></li>')
            out.append(f'              <li><a href="{h(e["pdf"])}">PDF</a></li>')
            out.append(f'              <li><a href="{h(e["source"])}">Source and reproduction</a></li>')
            out.append('            </ul>')
        else:
            out.append(f'            <p class="entry-meta"><time datetime="{e["date"]}">{e["date"]}</time> &middot; <span class="tag">{h(e["kind"])}</span></p>')
            out.append(f'            <h3><a href="{h(e["url"])}">{h(e["title"])}</a></h3>')
            out.append(f'            <p>{h(e["home_summary"])}</p>')
        out.append('          </li>')
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ research archive

def papers_block() -> str:
    out = []
    for e in sorted(PAPERS, key=lambda e: e["date"], reverse=True):
        cite = h(plain_citation(e))
        out += [
            f'          <li class="entry" id="{e["id"]}">',
            f'            <p class="entry-meta"><time datetime="{e["date"]}">{e["date"]}</time> &middot; <span class="tag">{h(e["status"])}</span> &middot; version {h(e["version"])} &middot; {h(e["license"])}</p>',
            f'            <h3><a href="./{paper_path(e)}">{h(e["title"])}</a></h3>',
            f'            <p>{h(e["subtitle"])}</p>',
            f'            <p>{h(e["archive_summary"])}</p>',
            '            <ul class="inline-links">',
            f'              <li><a href="./{paper_path(e)}">Paper page</a></li>',
            f'              <li><a href="{doi_url(e)}">DOI {h(e["doi"])}</a></li>',
            f'              <li><a href="{h(e["pdf"])}">PDF</a></li>',
            f'              <li><a href="{h(e["source"])}">Source</a></li>',
            f'              <li><a href="{h(e["release"])}">Release</a></li>',
            '            </ul>',
            '            <details>',
            '              <summary>Cite this paper</summary>',
            f'              <pre class="code-snippet" tabindex="0"><code>{cite}</code></pre>',
            '            </details>',
            '          </li>',
        ]
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ paper pages

def shared_chrome() -> tuple[str, str, str]:
    """Header, footer, and CSP are copied from research.html so every page shares one navigation."""
    src = (ROOT / "research.html").read_text(encoding="utf-8")
    csp = re.search(r'  <meta http-equiv="Content-Security-Policy"[^>]*>\n', src).group(0)
    header = re.search(r'  <header class="site-header">.*?</header>\n', src, re.S).group(0)
    footer = re.search(r'  <footer class="site-footer">.*?</footer>\n', src, re.S).group(0)
    header = header.replace(' aria-current="page"', "")

    def relink(block: str) -> str:
        return block.replace('href="./', 'href="../')

    return csp, relink(header), relink(footer)


def paper_page(e: dict) -> str:
    csp, header, footer = shared_chrome()
    url = BASE + paper_path(e)
    title = f"{e['title']} | THOR-SEC"
    desc = e["description"]
    assert len(desc) <= 160, f"{e['id']}: description over 160 characters"
    date_slash = e["date"].replace("-", "/")
    abstract = "\n".join(f"          <p>{h(p)}</p>" for p in e["abstract"])
    limits = "\n".join(f"          <li>{h(item)}</li>" for item in e["limitations"])
    versions = "\n".join(
        f'          <li>Version {h(v["version"])}<span class="sub"><time datetime="{v["date"]}">{v["date"]}</time> &middot; {h(v["note"])}</span></li>'
        for v in e["versions"]
    )
    defensive = ""
    if e.get("defensive_publication"):
        defensive = (
            '\n\n    <section aria-labelledby="disclosure-heading">\n'
            '      <div class="container">\n'
            '        <h2 id="disclosure-heading">Disclosure status</h2>\n'
            '        <p class="prose">Appendix A of the paper is a reference claim set released as a defensive publication. '
            'It places the mechanism in the public record as prior art. No patent or filing status is claimed. '
            'See <a href="../inventions.html">Inventions</a>.</p>\n'
            '      </div>\n'
            '    </section>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
{csp.rstrip()}
  <meta name="referrer" content="no-referrer">
  <meta name="color-scheme" content="dark light">
  <meta name="author" content="{h(SITE['author'])}">
  <meta name="robots" content="index,follow">
  <title>{h(title)}</title>
  <meta name="description" content="{h(desc)}">
  <link rel="canonical" href="{url}">
  <link rel="author" href="https://orcid.org/{SITE['orcid']}">
  <link rel="alternate" type="application/atom+xml" title="THOR-SEC Research" href="{BASE}feed.xml">
  <meta name="citation_title" content="{h(e['full_title'])}">
  <meta name="citation_author" content="{h(SITE['author_citation'])}">
  <meta name="citation_publication_date" content="{date_slash}">
  <meta name="citation_publisher" content="{h(e['publisher'])}">
  <meta name="citation_doi" content="{h(e['doi'])}">
  <meta name="citation_pdf_url" content="{h(e['pdf'])}">
  <meta name="citation_abstract_html_url" content="{url}">
  <meta name="citation_language" content="en">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="THOR-SEC">
  <meta property="og:title" content="{h(title)}">
  <meta property="og:description" content="{h(desc)}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="{SOCIAL_IMAGE}">
  <meta property="og:image:type" content="image/png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="{SOCIAL_ALT}">
  <meta property="og:locale" content="en_US">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{h(title)}">
  <meta name="twitter:description" content="{h(desc)}">
  <meta name="twitter:image" content="{SOCIAL_IMAGE}">
  <meta name="twitter:image:alt" content="{SOCIAL_ALT}">
  <link rel="stylesheet" href="../styles.css">
  <link rel="icon" type="image/png" sizes="96x96" href="../assets/favicon.png">
  <link rel="apple-touch-icon" href="../assets/apple-touch-icon.png">
  <meta name="theme-color" content="#0a0c0f" media="(prefers-color-scheme: dark)">
  <meta name="theme-color" content="#f6f6f3" media="(prefers-color-scheme: light)">
</head>
<body>
  <a class="skip-link" href="#main">Skip to main content</a>
{header}
  <main id="main">
    <div class="page-head">
      <div class="container">
        <p class="eyebrow">Research paper &middot; <a href="../research.html">Research archive</a></p>
        <h1>{h(e['title'])}</h1>
        <p class="lead">{h(e['subtitle'])}</p>
        <p class="entry-meta"><time datetime="{e['date']}">{e['date']}</time> &middot; <span class="tag">{h(e['status'])}</span> &middot; version {h(e['version'])} &middot; {h(e['license'])} &middot; DOI {h(e['doi'])}</p>
        <div class="actions">
          <a class="btn btn-primary" href="{h(e['pdf'])}">Read the paper (PDF)</a>
          <a class="btn btn-secondary" href="{doi_url(e)}">DOI record</a>
        </div>
      </div>
    </div>

    <section aria-labelledby="status-heading">
      <div class="container">
        <div class="panel">
          <h2 id="status-heading">Research status</h2>
          <p class="prose">{h(e['status_note'])}</p>
        </div>
      </div>
    </section>

    <section aria-labelledby="abstract-heading">
      <div class="container">
        <h2 id="abstract-heading">Abstract</h2>
        <div class="prose">
{abstract}
        </div>
      </div>
    </section>

    <section aria-labelledby="limits-heading">
      <div class="container">
        <h2 id="limits-heading">Known limitations</h2>
        <ul class="bullet-list prose">
{limits}
        </ul>
        <p class="note">Summarized from the paper. The full list is in its section on limitations, failure modes, and open research problems.</p>
      </div>
    </section>

    <section aria-labelledby="artifacts-heading">
      <div class="container">
        <h2 id="artifacts-heading">Artifacts</h2>
        <ul class="contact-grid">
          <li><span>DOI</span><a href="{doi_url(e)}">{h(e['doi'])}</a></li>
          <li><span>Paper</span><a href="{h(e['pdf'])}">PDF, version {h(e['version'])}</a></li>
          <li><span>Source</span><a href="{h(e['source'])}">Paper source and reproduction script</a></li>
          <li><span>Release</span><a href="{h(e['release'])}">Version {h(e['version'])}</a></li>
          <li><span>Archive</span><a href="{h(e['record'])}">{h(e['publisher'])} record</a></li>
          <li><span>Author</span><a href="https://orcid.org/{SITE['orcid']}">ORCID {SITE['orcid']}</a></li>
        </ul>
      </div>
    </section>

    <section aria-labelledby="cite-heading">
      <div class="container">
        <h2 id="cite-heading">Cite this work</h2>
        <p class="code-label">Plain text</p>
        <pre class="code-snippet" tabindex="0"><code>{h(plain_citation(e))}</code></pre>
        <p class="code-label">BibTeX</p>
        <pre class="code-snippet" tabindex="0"><code>{h(bibtex(e))}</code></pre>
      </div>
    </section>

    <section aria-labelledby="versions-heading">
      <div class="container">
        <h2 id="versions-heading">Version history</h2>
        <ul class="plain-list">
{versions}
        </ul>
      </div>
    </section>{defensive}
  </main>

{footer}</body>
</html>
"""


# ------------------------------------------------------------------ feed and sitemap

def feed() -> str:
    items = sorted((e for e in ENTRIES if e.get("feed_summary")), key=lambda e: (e["updated"], e["date"]), reverse=True)
    updated = max(e["updated"] for e in items)
    out = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom">',
        f"  <title>{h(SITE['feed_title'])}</title>",
        f'  <link href="{BASE}" rel="alternate"/>',
        f'  <link href="{BASE}feed.xml" rel="self"/>',
        f"  <id>{BASE}feed.xml</id>",
        f"  <updated>{updated}T00:00:00Z</updated>",
        "  <author>",
        f"    <name>{h(SITE['author'])}</name>",
        f"    <uri>https://orcid.org/{SITE['orcid']}</uri>",
        "  </author>",
    ]
    for e in items:
        link = BASE + paper_path(e) if e["kind"] == "paper" else e["url"]
        entry_id = e.get("feed_id", link)
        out += [
            "",
            "  <entry>",
            f"    <title>{h(e['title'])}</title>",
            f'    <link href="{h(link)}" rel="alternate"/>',
            f"    <id>{h(entry_id)}</id>",
            f"    <updated>{e['updated']}T00:00:00Z</updated>",
            f"    <published>{e['date']}T00:00:00Z</published>",
            f"    <summary>{h(e['feed_summary'])}</summary>",
            "  </entry>",
        ]
    out.append("</feed>")
    return "\n".join(out) + "\n"


def sitemap() -> str:
    rows = [(BASE + p["path"], p["lastmod"]) for p in DATA["sitemap"]]
    rows += [(BASE + paper_path(e), e["updated"]) for e in PAPERS]
    if CASE_STUDIES:
        rows += [(BASE + "case-studies.html", max(e.get("updated", "2026-09-28") for e in CASE_STUDIES))]
        rows += [(BASE + f"case-studies/{e['id']}.html", e.get("updated", "2026-09-28")) for e in CASE_STUDIES]
    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod in rows:
        out += ["  <url>", f"    <loc>{h(loc)}</loc>", f"    <lastmod>{lastmod}</lastmod>", "  </url>"]
    out.append("</urlset>")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ main

def outputs() -> dict[Path, str]:
    result: dict[Path, str] = {}
    home = (ROOT / "index.html").read_text(encoding="utf-8")
    result[Path("index.html")] = replace_block(home, "latest", latest_block(), "index.html")
    archive = (ROOT / "research.html").read_text(encoding="utf-8")
    result[Path("research.html")] = replace_block(archive, "papers", papers_block(), "research.html")
    for e in PAPERS:
        result[Path(paper_path(e))] = paper_page(e)
    result[Path("feed.xml")] = feed()
    result[Path("sitemap.xml")] = sitemap()
    return result


def main() -> None:
    check = "--check" in sys.argv[1:]
    expected = outputs()
    stale = []
    known = {Path(paper_path(e)) for e in PAPERS}
    orphans = [p.relative_to(ROOT) for p in (ROOT / "research").glob("*.html") if p.relative_to(ROOT) not in known] if (ROOT / "research").is_dir() else []
    for rel, text in expected.items():
        target = ROOT / rel
        current = target.read_text(encoding="utf-8") if target.exists() else None
        if current == text:
            continue
        stale.append(rel)
        if not check:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
    if check:
        if stale or orphans:
            print("RESEARCH BUILD OUT OF DATE")
            for rel in stale:
                print(f"- {rel} does not match scripts/research.json (run python3 scripts/build_research.py)")
            for rel in orphans:
                print(f"- {rel} has no entry in scripts/research.json")
            raise SystemExit(1)
        print(f"RESEARCH BUILD UP TO DATE ({len(expected)} outputs, {len(PAPERS)} paper page(s))")
        return
    if orphans:
        print("Warning: pages with no entry in scripts/research.json: " + ", ".join(map(str, orphans)))
    print(f"Wrote {len(stale)} file(s): " + (", ".join(map(str, stale)) if stale else "none (already up to date)"))


if __name__ == "__main__":
    main()
