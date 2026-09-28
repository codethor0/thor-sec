#!/usr/bin/env python3
from __future__ import annotations

from html import escape
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "scripts/case_studies.json").read_text(encoding="utf-8"))
SITE = DATA["site"]
ENTRIES = DATA["entries"]
BASE = SITE["base"]
ALLOWED = {"formal-design", "implemented-and-tested", "prototype", "empirical"}
SOCIAL_IMAGE = BASE + "assets/thor-sec-social-card.png"
SOCIAL_ALT = "THOR-SEC: independent security research by Thor Thor"


def h(text: str) -> str:
    return escape(str(text), quote=False).replace('"', "&quot;")


def path_for(e: dict) -> str:
    return f"case-studies/{e['id']}.html"


def validate() -> None:
    seen = set()
    required = {"id", "title", "eyebrow", "evidence_status", "evidence_label", "featured_order", "description", "problem", "common_failures", "approach", "evidence", "limitations", "status", "artifacts"}
    for e in ENTRIES:
        missing = sorted(required - set(e))
        if missing:
            raise SystemExit(f"{e.get('id', '<unknown>')}: missing fields: {', '.join(missing)}")
        if e["id"] in seen:
            raise SystemExit(f"duplicate case-study id: {e['id']}")
        seen.add(e["id"])
        if not re.fullmatch(r"[a-z0-9-]+", e["id"]):
            raise SystemExit(f"{e['id']}: invalid id")
        if e["evidence_status"] not in ALLOWED:
            raise SystemExit(f"{e['id']}: evidence_status must be one of {sorted(ALLOWED)}")
        if not e["limitations"]:
            raise SystemExit(f"{e['id']}: limitations must not be empty")
        if len(e["description"]) > 170:
            raise SystemExit(f"{e['id']}: description is too long")
        for key in ("problem", "common_failures", "approach", "evidence"):
            if not e[key]:
                raise SystemExit(f"{e['id']}: {key} must not be empty")
        if not e["artifacts"]:
            raise SystemExit(f"{e['id']}: artifacts must not be empty")


def nav(depth: int, current: str = "") -> str:
    p = "../" if depth else "./"
    def item(label: str, href: str, key: str, cls: str = "") -> str:
        attrs = []
        if cls:
            attrs.append(f'class="{cls}"')
        if current == key:
            attrs.append('aria-current="page"')
        a = (" " + " ".join(attrs)) if attrs else ""
        return f'            <li><a{a} href="{p}{href}">{label}</a></li>'
    return "\n".join([
        '  <header class="site-header">',
        '    <div class="container">',
        f'      <a class="site-brand" href="{p}">THOR-SEC</a>',
        '      <div class="header-right">',
        '        <nav class="site-nav" aria-label="Primary">',
        '          <ul>',
        item("Research", "research.html", "research"),
        item("Case Studies", "case-studies.html", "case-studies"),
        f'            <li><a href="{p}#projects">Projects</a></li>',
        f'            <li><a href="{p}#writing">Writing</a></li>',
        item("About", "about.html", "about"),
        item("Commission", "work.html", "work", "nav-cta"),
        '          </ul>',
        '        </nav>',
        '      </div>',
        '    </div>',
        '  </header>',
    ])


def footer(depth: int) -> str:
    p = "../" if depth else "./"
    return f'''  <footer class="site-footer">
    <div class="container">
      <ul>
        <li><a href="{p}research.html">Research</a></li>
        <li><a href="{p}case-studies.html">Case Studies</a></li>
        <li><a href="{p}inventions.html">Inventions</a></li>
        <li><a href="{p}work.html">Commission research</a></li>
        <li><a href="{p}about.html">About</a></li>
        <li><a href="{p}now.html">Now</a></li>
        <li><a href="{p}security.html">Site security</a></li>
        <li><a href="{p}.well-known/security.txt">security.txt</a></li>
        <li><a href="{p}feed.xml">RSS/Atom</a></li>
        <li><a href="https://github.com/codethor0/thor-sec">Source</a></li>
      </ul>
      <p>&copy; 2026 THOR-SEC &middot; Thor Thor &middot; Independent research, not affiliated with any employer &middot; Last updated September 2026</p>
    </div>
  </footer>'''


def head(title: str, description: str, canonical: str, depth: int, evidence_status: str | None = None) -> str:
    p = "../" if depth else ""
    extra = f'  <meta name="thor-sec:evidence-status" content="{h(evidence_status)}">\n' if evidence_status else ""
    return f'''<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; base-uri 'self'; object-src 'none'; form-action 'none'; img-src 'self'; style-src 'self'; script-src 'none'; connect-src 'none'; font-src 'self'; media-src 'self'; frame-src 'none'; worker-src 'none'; manifest-src 'none'; upgrade-insecure-requests">
  <meta name="referrer" content="no-referrer">
  <meta name="color-scheme" content="dark light">
  <meta name="author" content="{h(SITE['author'])}">
  <meta name="robots" content="index,follow">
{extra}  <title>{h(title)}</title>
  <meta name="description" content="{h(description)}">
  <link rel="canonical" href="{h(canonical)}">
  <link rel="author" href="https://orcid.org/0009-0001-6573-385X">
  <link rel="alternate" type="application/atom+xml" title="THOR-SEC Research" href="{BASE}feed.xml">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="THOR-SEC">
  <meta property="og:title" content="{h(title)}">
  <meta property="og:description" content="{h(description)}">
  <meta property="og:url" content="{h(canonical)}">
  <meta property="og:image" content="{SOCIAL_IMAGE}">
  <meta property="og:image:type" content="image/png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="{SOCIAL_ALT}">
  <meta property="og:locale" content="en_US">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{h(title)}">
  <meta name="twitter:description" content="{h(description)}">
  <meta name="twitter:image" content="{SOCIAL_IMAGE}">
  <meta name="twitter:image:alt" content="{SOCIAL_ALT}">
  <link rel="stylesheet" href="{p}styles.css">
  <link rel="icon" type="image/png" sizes="96x96" href="{p}assets/favicon.png">
  <link rel="apple-touch-icon" href="{p}assets/apple-touch-icon.png">
  <meta name="theme-color" content="#0a0c0f" media="(prefers-color-scheme: dark)">
  <meta name="theme-color" content="#f6f6f3" media="(prefers-color-scheme: light)">
</head>'''


def ul(items: list[str]) -> str:
    return "\n".join(f"          <li>{h(item)}</li>" for item in items)


def prose(items: list[str]) -> str:
    return "\n".join(f"          <p>{h(item)}</p>" for item in items)


def archive_page() -> str:
    cards = []
    for e in sorted(ENTRIES, key=lambda x: x["featured_order"]):
        cards += [
            '          <li class="card">',
            f'            <p class="card-kind">{h(e["evidence_label"])}</p>',
            f'            <h3><a href="./{path_for(e)}">{h(e["title"])}</a></h3>',
            f'            <p>{h(e["description"])}</p>',
            f'            <p class="card-foot"><a href="./{path_for(e)}">Read case study</a></p>',
            '          </li>',
        ]
    cards_text = "\n".join(cards)
    title = "Case Studies | THOR-SEC"
    desc = "Evidence-labeled THOR-SEC case studies separating formal designs, implemented and tested systems, prototypes, and empirical results."
    return f'''<!DOCTYPE html>
<html lang="en">
{head(title, desc, BASE + "case-studies.html", 0)}
<body>
  <a class="skip-link" href="#main">Skip to main content</a>
{nav(0, "case-studies")}
  <main id="main">
    <div class="page-head">
      <div class="container">
        <p class="eyebrow">Evidence before claims</p>
        <h1>Case Studies</h1>
        <p class="lead">{h(SITE['tagline'])} Each case study states the problem, the approach, the evidence, the limitations, and the current status.</p>
      </div>
    </div>

    <section aria-labelledby="cases-heading">
      <div class="container">
        <div class="section-head">
          <h2 id="cases-heading">Current case studies</h2>
          <a class="section-link" href="./research.html">Research archive</a>
        </div>
        <ul class="card-grid">
{cards_text}
        </ul>
      </div>
    </section>

    <section aria-labelledby="labels-heading">
      <div class="container">
        <h2 id="labels-heading">Evidence labels</h2>
        <ul class="plain-list prose">
          <li><strong>Formal design</strong><span class="sub">Architecture, model, or proposal with defined reasoning or evaluation methods but without empirical efficacy results.</span></li>
          <li><strong>Implemented and tested</strong><span class="sub">Working implementation with automated evidence for stated invariants; not automatically a production-readiness claim.</span></li>
          <li><strong>Prototype</strong><span class="sub">Implemented system or tool whose validation or release gates are still incomplete.</span></li>
          <li><strong>Empirical</strong><span class="sub">Results backed by measurements under a documented method and population. No current THOR-SEC case study uses this label.</span></li>
        </ul>
      </div>
    </section>
  </main>
{footer(0)}
</body>
</html>
'''


def case_page(e: dict) -> str:
    title = f"{e['title']} Case Study | THOR-SEC"
    canonical = BASE + path_for(e)
    artifacts = "\n".join(
        f'          <li><span>{h(label)}</span><a href="{h(url)}">{h(text)}</a></li>'
        for label, url, text in e["artifacts"]
    )
    return f'''<!DOCTYPE html>
<html lang="en">
{head(title, e['description'], canonical, 1, e['evidence_status'])}
<body>
  <a class="skip-link" href="#main">Skip to main content</a>
{nav(1)}
  <main id="main">
    <div class="page-head">
      <div class="container">
        <p class="eyebrow">{h(e['eyebrow'])} &middot; <a href="../case-studies.html">Case Studies</a></p>
        <h1>{h(e['title'])}</h1>
        <p class="lead">{h(e['description'])}</p>
        <p class="entry-meta"><span class="tag">{h(e['evidence_status'])}</span> &middot; {h(e['evidence_label'])}</p>
      </div>
    </div>

    <section aria-labelledby="problem-heading">
      <div class="container">
        <h2 id="problem-heading">Problem</h2>
        <div class="prose">
{prose(e['problem'])}
        </div>
      </div>
    </section>

    <section aria-labelledby="common-heading">
      <div class="container">
        <h2 id="common-heading">Why common approaches fall short</h2>
        <ul class="bullet-list prose">
{ul(e['common_failures'])}
        </ul>
      </div>
    </section>

    <section aria-labelledby="approach-heading">
      <div class="container">
        <h2 id="approach-heading">THOR-SEC approach</h2>
        <div class="prose">
{prose(e['approach'])}
        </div>
      </div>
    </section>

    <section aria-labelledby="evidence-heading">
      <div class="container">
        <h2 id="evidence-heading">Evidence</h2>
        <ul class="bullet-list prose">
{ul(e['evidence'])}
        </ul>
      </div>
    </section>

    <section aria-labelledby="limitations-heading">
      <div class="container">
        <h2 id="limitations-heading">Limitations</h2>
        <ul class="bullet-list prose">
{ul(e['limitations'])}
        </ul>
      </div>
    </section>

    <section aria-labelledby="status-heading">
      <div class="container">
        <div class="panel panel-accent">
          <p class="eyebrow">Current status</p>
          <h2 id="status-heading">{h(e['evidence_label'])}</h2>
          <p class="prose">{h(e['status'])}</p>
        </div>
      </div>
    </section>

    <section aria-labelledby="artifacts-heading">
      <div class="container">
        <h2 id="artifacts-heading">Artifacts</h2>
        <ul class="contact-grid">
{artifacts}
        </ul>
      </div>
    </section>
  </main>
{footer(1)}
</body>
</html>
'''


def home_block() -> str:
    cards = []
    for e in sorted(ENTRIES, key=lambda x: x["featured_order"]):
        cards += [
            '          <li class="card">',
            f'            <p class="card-kind">{h(e["evidence_label"])}</p>',
            f'            <h3><a href="./{path_for(e)}">{h(e["title"])}</a></h3>',
            f'            <p>{h(e["description"])}</p>',
            '          </li>',
        ]
    return "\n".join(cards) + "\n"


def replace_block(text: str, name: str, body: str, path: str) -> str:
    start = f"<!-- build:{name}:start -->"
    end = f"<!-- build:{name}:end -->"
    pattern = re.compile(re.escape(start) + r".*?" + r"([ \\t]*)" + re.escape(end), re.S)
    m = pattern.search(text)
    if not m:
        raise SystemExit(f"{path}: build markers for '{name}' not found")
    indent = m.group(1)
    return text[:m.start()] + start + "\n" + body + indent + end + text[m.end():]


def outputs() -> dict[Path, str]:
    home = (ROOT / "index.html").read_text(encoding="utf-8")
    result = {
        Path("index.html"): replace_block(home, "case-studies", home_block(), "index.html"),
        Path("case-studies.html"): archive_page(),
    }
    for e in ENTRIES:
        result[Path(path_for(e))] = case_page(e)
    return result


def main() -> None:
    validate()
    check = "--check" in sys.argv[1:]
    expected = outputs()
    known = {Path(path_for(e)) for e in ENTRIES}
    case_dir = ROOT / "case-studies"
    orphans = [p.relative_to(ROOT) for p in case_dir.glob("*.html") if p.relative_to(ROOT) not in known] if case_dir.is_dir() else []
    stale = []
    for rel, content in expected.items():
        target = ROOT / rel
        current = target.read_text(encoding="utf-8") if target.exists() else None
        if current == content:
            continue
        stale.append(rel)
        if not check:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
    if check:
        if stale or orphans:
            print("CASE STUDY BUILD OUT OF DATE")
            for rel in stale:
                print(f"- {rel} does not match scripts/case_studies.json")
            for rel in orphans:
                print(f"- {rel} has no entry in scripts/case_studies.json")
            raise SystemExit(1)
        print(f"CASE STUDY BUILD UP TO DATE ({len(expected)} outputs, {len(ENTRIES)} case study page(s))")
        return
    if orphans:
        print("Warning: orphan case-study pages: " + ", ".join(map(str, orphans)))
    print(f"Wrote {len(stale)} case-study output(s)")


if __name__ == "__main__":
    main()
