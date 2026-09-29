#!/usr/bin/env python3
# Fail-closed static security audit for the THOR-SEC public site.

from __future__ import annotations

from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
HTML_FILES = [
    Path("index.html"),
    Path("research.html"),
    Path("case-studies.html"),
    Path("work.html"),
    Path("about.html"),
    Path("inventions.html"),
    Path("security.html"),
    Path("now.html"),
    Path("404.html"),
    Path("request-received.html"),
    # Paper pages built from scripts/research.json.
    *sorted(p.relative_to(ROOT) for p in (ROOT / "research").glob("*.html")),
    # Evidence-labeled case studies built from scripts/case_studies.json.
    *sorted(p.relative_to(ROOT) for p in (ROOT / "case-studies").glob("*.html")),
]
PAPER_META = (
    'name="citation_title"', 'name="citation_author"', 'name="citation_publication_date"',
    'name="citation_doi"', 'name="citation_pdf_url"',
)
REQUIRED_FILES = [
    *HTML_FILES,
    Path("styles.css"),
    Path("README.md"),
    Path("SECURITY.md"),
    Path("LICENSE"),
    Path("robots.txt"),
    Path("sitemap.xml"),
    Path("feed.xml"),
    Path(".nojekyll"),
    Path(".gitignore"),
    Path(".well-known/security.txt"),
    Path(".github/CODEOWNERS"),
    Path("_headers"),
    Path("wrangler.jsonc"),
    Path(".assetsignore"),
    Path("ARCHITECTURE.md"),
    Path("worker/intake.mjs"),
    Path("worker/intake.test.mjs"),
    Path("assets/fonts/InterVariable.woff2"),
    Path("assets/fonts/LICENSE-Inter.txt"),
    Path("assets/thor-sec-social-card.png"),
    Path("assets/favicon.png"),
    Path("assets/apple-touch-icon.png"),
    Path("scripts/build_research.py"),
    Path("scripts/research.json"),
    Path("scripts/build_case_studies.py"),
    Path("scripts/case_studies.json"),
    Path("scripts/build_inventions.py"),
    Path("scripts/invention_publications.json"),
    Path("INVENTION-GATE.md"),
]
CANONICAL_BASE = "https://codethor0.github.io/thor-sec/"
REQUIRED_META = (
    'property="og:title"', 'property="og:description"', 'property="og:url"',
    'property="og:image"', 'property="og:image:alt"', 'property="og:image:width"',
    'property="og:image:height"', 'property="og:locale"', 'name="twitter:card"',
    'name="twitter:title"', 'name="twitter:description"', 'name="twitter:image"',
    'name="twitter:image:alt"', 'rel="icon"', 'rel="apple-touch-icon"', 'name="theme-color"',
)
MISSION = "THOR-SEC finds hard security and infrastructure problems, develops original solutions, and publishes the evidence that they work."
MISSION_PAGES = (Path("index.html"), Path("about.html"))
NAV_TARGETS = ("research.html", "case-studies.html", "about.html", "work.html")
FOOTER_TARGETS = ("research.html", "case-studies.html", "work.html")
HOME_REQUEST_LINK = 'href="./work.html#request"'
FORM_PAGE = Path("work.html")
FORM_ACTION = "https://thor-sec.codethor0.workers.dev/api/request"
FORM_ACTION_CSP = "form-action https://thor-sec.codethor0.workers.dev https://codethor0.github.io"
# name: maxlength (None for selects/checkboxes); must mirror worker/intake.mjs FIELDS.
FORM_FIELDS = {
    "name": "120", "email": "254", "organization": "200", "question": "2500",
    "objective": "1500", "scope": "2000", "timeline": "200", "budget": "200",
    "notes": "2500", "authorization": None, "publication": None, "website": None, "confirm": None,
}
FORM_OPTIONS = {
    "authorization": {"", "owner", "written", "planning", "other"},
    "publication": {"public", "delayed", "private", "unsure"},
}
REQUIRED_ASSET_IGNORES = (".git", ".github", ".wrangler", "scripts", "worker", "wrangler.jsonc", ".assetsignore", "ARCHITECTURE.md", "INVENTION-GATE.md", "README.md", "SECURITY.md")

REQUIRED_CSP_TOKENS = [
    "default-src 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "img-src 'self'",
    "style-src 'self'",
    "script-src 'none'",
    "connect-src 'none'",
    "frame-src 'none'",
    "worker-src 'none'",
]
FORBIDDEN_CSP_TOKENS = ["'unsafe-inline'", "'unsafe-eval'", "data:", "http:"]
FORBIDDEN_TAGS = {"script", "iframe", "object", "embed"}
BAD_SCHEMES = {"javascript", "data", "vbscript", "file"}
SECRET_PATTERNS = {
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "generic private key": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
}
ATTRIBUTION_PATTERNS = [
    re.compile(r"co-authored-by:", re.I),
    re.compile(r"generated (?:by|with)", re.I),
    re.compile(r"assistant attribution", re.I),
    re.compile(r"tool attribution", re.I),
    re.compile(r"master prompt", re.I),
    re.compile(r"prompt artifact", re.I),
    re.compile(r"private build workflow", re.I),
]


class PageParser(HTMLParser):
    def __init__(self, path: Path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.ids: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.csp: str | None = None
        self.referrer: str | None = None
        self.errors: list[str] = []
        self.forms: list[dict[str, str | None]] = []
        self.controls: list[tuple[str, dict[str, str | None]]] = []
        self.options: dict[str, set[str]] = {}
        self._select: str | None = None

    def handle_endtag(self, tag: str):
        if tag.lower() == "select":
            self._select = None

    def handle_starttag(self, tag: str, attrs_list):
        tag = tag.lower()
        attrs = {k.lower(): v for k, v in attrs_list if k}

        if tag in FORBIDDEN_TAGS:
            self.errors.append(f"{self.path}: forbidden <{tag}> tag")

        for key in attrs:
            if key == "style":
                self.errors.append(f"{self.path}: inline style attribute is forbidden")
            if key.startswith("on"):
                self.errors.append(f"{self.path}: inline event handler {key}= is forbidden")

        if tag == "form":
            self.forms.append(attrs)
        if tag in ("input", "textarea", "select", "button"):
            self.controls.append((tag, attrs))
        if tag == "select":
            self._select = attrs.get("name") or ""
        if tag == "option" and self._select is not None:
            self.options.setdefault(self._select, set()).add(attrs.get("value") or "")

        if "id" in attrs and attrs["id"]:
            self.ids.append(attrs["id"])

        for attr in ("href", "src"):
            value = attrs.get(attr)
            if value:
                self.links.append((attr, value))

        if tag == "source" and attrs.get("srcset"):
            self.links.append(("srcset", attrs["srcset"].split()[0]))

        if tag == "meta":
            http_equiv = (attrs.get("http-equiv") or "").lower()
            name = (attrs.get("name") or "").lower()
            if http_equiv == "content-security-policy":
                self.csp = attrs.get("content") or ""
            if name == "referrer":
                self.referrer = attrs.get("content") or ""


def resolve_local(base: Path, value: str) -> tuple[Path | None, str | None]:
    if value.startswith("#"):
        return base, value[1:]

    parsed = urlparse(value)
    if parsed.scheme:
        return None, None

    raw_path = unquote(parsed.path)
    fragment = parsed.fragment or None

    if raw_path in ("", "."):
        target = base
    elif raw_path in ("./", "/"):
        target = Path("index.html")
    else:
        target = Path((base.parent / raw_path).as_posix())

    return target, fragment


def check_forms(pages: dict[Path, PageParser]) -> list[str]:
    errors: list[str] = []
    for rel, parser in pages.items():
        if rel != FORM_PAGE:
            if parser.forms or parser.controls:
                errors.append(f"{rel}: forms and form controls are only permitted on {FORM_PAGE}")
            continue
        if len(parser.forms) != 1:
            errors.append(f"{rel}: exactly one form is required, found {len(parser.forms)}")
            continue
        form = parser.forms[0]
        if (form.get("method") or "").lower() != "post" or form.get("action") != FORM_ACTION:
            errors.append(f"{rel}: form must POST to {FORM_ACTION}")
        if form.get("enctype") not in (None, "application/x-www-form-urlencoded"):
            errors.append(f"{rel}: form must use the default urlencoded encoding")
        named: dict[str, dict[str, str | None]] = {}
        for tag, attrs in parser.controls:
            kind = (attrs.get("type") or "").lower()
            if kind in ("file", "password", "hidden"):
                errors.append(f"{rel}: <input type={kind}> is forbidden")
            if attrs.get("name"):
                named[attrs["name"]] = attrs
        if set(named) != set(FORM_FIELDS):
            errors.append(f"{rel}: form fields must be exactly {sorted(FORM_FIELDS)}, found {sorted(named)}")
        for name, maxlength in FORM_FIELDS.items():
            if name in named and maxlength and named[name].get("maxlength") != maxlength:
                errors.append(f"{rel}: field {name} must have maxlength={maxlength}")
        for name in ("name", "email", "question", "authorization", "confirm"):
            if name in named and "required" not in named[name]:
                errors.append(f"{rel}: field {name} must be required")
        if named.get("confirm", {}).get("value") != "yes":
            errors.append(f"{rel}: confirm checkbox must submit value yes")
        if named.get("website", {}).get("tabindex") != "-1":
            errors.append(f"{rel}: honeypot field must not be focusable")
        for name, values in FORM_OPTIONS.items():
            if parser.options.get(name) != values:
                errors.append(f"{rel}: {name} options must be exactly {sorted(values)}")
    return errors


def main() -> None:
    errors: list[str] = []

    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            errors.append(f"missing required file: {rel}")

    pages: dict[Path, PageParser] = {}

    for rel in HTML_FILES:
        full = ROOT / rel
        if not full.exists():
            continue

        text = full.read_text(encoding="utf-8")
        parser = PageParser(rel)
        parser.feed(text)
        pages[rel] = parser
        errors.extend(parser.errors)

        duplicates = sorted({item for item in parser.ids if parser.ids.count(item) > 1})
        if duplicates:
            errors.append(f"{rel}: duplicate id(s): {', '.join(duplicates)}")

        if True:
            if not parser.csp:
                errors.append(f"{rel}: missing Content-Security-Policy meta tag")
            else:
                for token in REQUIRED_CSP_TOKENS:
                    if token not in parser.csp:
                        errors.append(f"{rel}: CSP missing {token}")
                expected_fa = FORM_ACTION_CSP if rel == FORM_PAGE else "form-action 'none'"
                if expected_fa + ";" not in parser.csp:
                    errors.append(f"{rel}: CSP must contain exactly {expected_fa}")
                for token in FORBIDDEN_CSP_TOKENS:
                    if token in parser.csp:
                        errors.append(f"{rel}: CSP contains forbidden token {token}")

            if parser.referrer != "no-referrer":
                errors.append(f"{rel}: referrer policy must be no-referrer")

    errors.extend(check_forms(pages))

    id_maps = {rel: set(parser.ids) for rel, parser in pages.items()}

    for rel, parser in pages.items():
        for attr, value in parser.links:
            parsed = urlparse(value)

            if parsed.scheme.lower() in BAD_SCHEMES:
                errors.append(f"{rel}: forbidden URL scheme in {attr}: {value}")
                continue

            if parsed.scheme == "http":
                errors.append(f"{rel}: insecure external URL: {value}")
                continue

            if parsed.scheme in ("https", "mailto"):
                continue

            if value.startswith("//"):
                errors.append(f"{rel}: protocol-relative URL forbidden: {value}")
                continue

            target, fragment = resolve_local(rel, value)
            if target is None:
                continue

            full_target = ROOT / target
            if not full_target.exists():
                errors.append(f"{rel}: broken local reference {value} -> {target}")
                continue

            if fragment and target.suffix.lower() == ".html":
                if target in id_maps and fragment not in id_maps[target]:
                    errors.append(f"{rel}: missing fragment #{fragment} in {target}")

    for rel in (Path("feed.xml"), Path("sitemap.xml")):
        try:
            ET.parse(ROOT / rel)
        except Exception as exc:
            errors.append(f"{rel}: invalid XML: {exc}")

    security_txt = (ROOT / ".well-known/security.txt").read_text(encoding="utf-8")
    if "Canonical: https://codethor0.github.io/thor-sec/.well-known/security.txt" not in security_txt:
        errors.append("security.txt: missing canonical URL")
    match = re.search(r"^Expires:\s*(\S+)", security_txt, re.M)
    if not match:
        errors.append("security.txt: missing Expires field")
    else:
        try:
            expires = datetime.fromisoformat(match.group(1).replace("Z", "+00:00"))
            if expires <= datetime.now(timezone.utc):
                errors.append("security.txt: Expires value is not in the future")
        except ValueError:
            errors.append("security.txt: invalid Expires timestamp")

    headers_path = ROOT / "_headers"
    if headers_path.exists():
        headers_text = headers_path.read_text(encoding="utf-8")
        required_headers = (
            "Content-Security-Policy:",
            "frame-ancestors 'none'",
            "Referrer-Policy: no-referrer",
            "X-Content-Type-Options: nosniff",
            "X-Frame-Options: DENY",
            "Permissions-Policy:",
            "Cross-Origin-Opener-Policy: same-origin",
            "X-Permitted-Cross-Domain-Policies: none",
        )
        for required_header in required_headers:
            if required_header not in headers_text:
                errors.append(f"_headers: required policy missing: {required_header}")
        if "X-Robots-Tag: noindex" not in headers_text:
            errors.append("_headers: Cloudflare mirror must send X-Robots-Tag: noindex")
        if FORM_ACTION_CSP + ";" not in headers_text:
            errors.append(f"_headers: CSP must contain exactly {FORM_ACTION_CSP}")
        if "Strict-Transport-Security:" in headers_text:
            errors.append("_headers: HSTS must not be enabled before the Cloudflare custom domain is verified")

    ignore_path = ROOT / ".assetsignore"
    if ignore_path.exists():
        ignore_entries = {
            line.strip().strip("/")
            for line in ignore_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        for entry in REQUIRED_ASSET_IGNORES:
            if entry not in ignore_entries:
                errors.append(f".assetsignore: required exclusion missing: {entry}")

    wrangler_path = ROOT / "wrangler.jsonc"
    if wrangler_path.exists():
        wrangler_text = wrangler_path.read_text(encoding="utf-8")
        mains = re.findall(r'"main"\s*:\s*"([^"]*)"', wrangler_text)
        if mains != ["worker/intake.mjs"]:
            errors.append("wrangler.jsonc: the only permitted Worker entry point is worker/intake.mjs")
        if not re.search(r'"run_worker_first"\s*:\s*\[\s*"/api/request"\s*\]', wrangler_text):
            errors.append("wrangler.jsonc: Worker code must run first only for /api/request")
        if re.search(r'"observability"\s*:\s*\{\s*"enabled"\s*:\s*true', wrangler_text):
            errors.append("wrangler.jsonc: observability must stay disabled")
        if re.search(r'"(vars|secrets)"\s*:', wrangler_text):
            errors.append("wrangler.jsonc: secrets and vars must not be committed")
        if re.search(r'"account_id"\s*:', wrangler_text):
            errors.append("wrangler.jsonc: account_id must not be committed")
        if '"assets"' not in wrangler_text or '"404-page"' not in wrangler_text:
            errors.append("wrangler.jsonc: assets block with 404-page handling is required")

    for rel in HTML_FILES:
        page = (ROOT / rel).read_text(encoding="utf-8")
        for needle in REQUIRED_META:
            if needle not in page:
                errors.append(f"{rel}: missing metadata {needle}")
        for m in re.finditer(r'<link rel="canonical" href="([^"]+)"', page):
            if not m.group(1).startswith(CANONICAL_BASE):
                errors.append(f"{rel}: canonical must stay on GitHub Pages: {m.group(1)}")
        if re.search(r"fonts\.(googleapis|gstatic)\.com|@import\s", page):
            errors.append(f"{rel}: remote font or CSS import is forbidden")
    css = (ROOT / "styles.css").read_text(encoding="utf-8")
    if re.search(r"@import|url\(\s*[\"']?(https?:)?//", css):
        errors.append("styles.css: remote CSS or font URLs are forbidden")
    if 'url("assets/fonts/InterVariable.woff2")' not in css:
        errors.append("styles.css: self-hosted Inter @font-face missing")
    if "@media (prefers-color-scheme: light)" not in css:
        errors.append("styles.css: the light theme must follow the device setting")
    if "theme-toggle" in css:
        errors.append("styles.css: stateful theme toggle styles must not return")

    research_pages = [rel for rel in HTML_FILES if rel.parts[0] == "research"]
    if not research_pages:
        errors.append("research/: at least one paper page is required")
    for rel in research_pages:
        page = (ROOT / rel).read_text(encoding="utf-8")
        for needle in PAPER_META:
            if needle not in page:
                errors.append(f"{rel}: missing citation metadata {needle}")
        if f'<link rel="canonical" href="{CANONICAL_BASE}{rel.as_posix()}">' not in page:
            errors.append(f"{rel}: canonical URL must be {CANONICAL_BASE}{rel.as_posix()}")
        if rel.as_posix() not in (ROOT / "sitemap.xml").read_text(encoding="utf-8"):
            errors.append(f"sitemap.xml: {rel} must be listed")

    case_pages = [rel for rel in HTML_FILES if rel.parts[0] == "case-studies"]
    if len(case_pages) < 3:
        errors.append("case-studies/: three generated case-study pages are required")
    allowed_case_status = {"formal-design", "implemented-and-tested", "prototype", "empirical"}
    for rel in case_pages:
        page = (ROOT / rel).read_text(encoding="utf-8")
        m = re.search(r'<meta name="thor-sec:evidence-status" content="([^"]+)">', page)
        if not m or m.group(1) not in allowed_case_status:
            errors.append(f"{rel}: missing or invalid thor-sec:evidence-status")
        if 'id="limitations-heading"' not in page:
            errors.append(f"{rel}: limitations section is required")
        if 'id="status-heading"' not in page:
            errors.append(f"{rel}: current status section is required")
        if f'<link rel="canonical" href="{CANONICAL_BASE}{rel.as_posix()}">' not in page:
            errors.append(f"{rel}: canonical URL must be {CANONICAL_BASE}{rel.as_posix()}")
        if rel.as_posix() not in (ROOT / "sitemap.xml").read_text(encoding="utf-8"):
            errors.append(f"sitemap.xml: {rel} must be listed")
    if "case-studies.html" not in (ROOT / "sitemap.xml").read_text(encoding="utf-8"):
        errors.append("sitemap.xml: case-studies.html must be listed")

    # Navigation and mission must not silently regress on any page.
    for rel in HTML_FILES:
        text = (ROOT / rel).read_text(encoding="utf-8")
        for block, targets in (("nav", NAV_TARGETS), ("footer", FOOTER_TARGETS)):
            m = re.search(rf"<{block}\b.*?</{block}>", text, re.S)
            if not m:
                errors.append(f"{rel}: missing <{block}>")
                continue
            hrefs = {h.split("#")[0].lstrip("./") for h in re.findall(r'href="([^"]+)"', m.group(0))}
            for target in targets:
                if target not in hrefs:
                    errors.append(f"{rel}: {block} must link to {target}")
    for rel in MISSION_PAGES:
        if MISSION not in (ROOT / rel).read_text(encoding="utf-8"):
            errors.append(f"{rel}: mission statement missing or changed")
    if HOME_REQUEST_LINK not in (ROOT / "index.html").read_text(encoding="utf-8"):
        errors.append("index.html: commission call to action must link to work.html#request")

    invention_data = ROOT / "scripts/invention_publications.json"
    if invention_data.exists():
        import json
        try:
            public_disclosures = json.loads(invention_data.read_text(encoding="utf-8")).get("entries", [])
        except Exception as exc:
            errors.append(f"scripts/invention_publications.json: invalid JSON: {exc}")
            public_disclosures = []
        if not public_disclosures:
            errors.append("scripts/invention_publications.json: at least one intentional public disclosure is required")
        for item in public_disclosures:
            item_id = item.get("id", "<unknown>")
            if item.get("decision") != "publish-intentionally":
                errors.append(f"scripts/invention_publications.json: {item_id} is not publish-intentionally")
        inventions_page = (ROOT / "inventions.html").read_text(encoding="utf-8")
        if "<!-- build:public-disclosures:start -->" not in inventions_page or "<!-- build:public-disclosures:end -->" not in inventions_page:
            errors.append("inventions.html: public disclosure build markers are required")
        for item in public_disclosures:
            item_id = item.get("id", "")
            if item_id and f'data-disclosure-id="{item_id}"' not in inventions_page:
                errors.append(f"inventions.html: disclosure {item_id} is missing from generated page")

    public_suffixes = {".html", ".md", ".css", ".xml", ".txt", ".py", ".yml", ".yaml", ".sh", ".jsonc", ".js", ".mjs"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.suffix.lower() not in public_suffixes:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = path.relative_to(ROOT)
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                errors.append(f"{rel}: possible {label} detected")
        if rel.parts and rel.parts[0] in ("node_modules", ".wrangler"):
            continue
        if rel != Path("scripts/site_audit.py"):
            for pattern in ATTRIBUTION_PATTERNS:
                if pattern.search(text):
                    errors.append(f"{rel}: private-build attribution marker detected")

    received = (ROOT / "request-received.html").read_text(encoding="utf-8")
    if '<meta name="robots" content="noindex' not in received:
        errors.append("request-received.html: must be noindex")
    if "request-received" in (ROOT / "sitemap.xml").read_text(encoding="utf-8"):
        errors.append("sitemap.xml: request-received.html must not be listed")
    if 'mailto:codethor@gmail.com' not in (ROOT / FORM_PAGE).read_text(encoding="utf-8"):
        errors.append(f"{FORM_PAGE}: mailto fallback for research requests is required")

    home = (ROOT / "index.html").read_text(encoding="utf-8")
    for required in (
        "0009-0001-6573-385X",
        "10.5281/zenodo.23001045",
        "Mission-Invariant Architecture Morphing (MIAM)",
        "Model Identity Verifier",
        "BoundaryLayer",
        "Impact Forecast Algorithm (IFA)",
        "Security Stack Engineering (SSE)",
        "./research.html",
        "./security.html",
        "./inventions.html",
    ):
        if required not in home:
            errors.append(f"index.html: required public record missing: {required}")

    if errors:
        print("STATIC SITE AUDIT FAILED")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("STATIC SITE AUDIT PASSED")
    print(f"HTML pages checked: {len(pages)}")
    print("Active content: none (one POST form on work.html)")
    print("Inline event handlers/styles: none")
    print("Local references: OK")
    print("CSP/referrer policy: OK")
    print("XML: OK")
    print("security.txt: OK")
    print("Cloudflare asset exclusions: OK")
    print("Public identity/research records: OK")
    print(f"Paper pages with citation metadata: {len([r for r in HTML_FILES if r.parts[0] == 'research'])}")
    print(f"Case-study pages with evidence labels: {len([r for r in HTML_FILES if r.parts[0] == 'case-studies'])}")
    print("Invention publication gate: OK")
    print("Navigation and mission: OK")


if __name__ == "__main__":
    main()
