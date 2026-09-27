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
    Path("inventions.html"),
    Path("security.html"),
    Path("now.html"),
    Path("404.html"),
]
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
]

REQUIRED_CSP_TOKENS = [
    "default-src 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "form-action 'none'",
    "img-src 'self'",
    "style-src 'self'",
    "script-src 'none'",
    "connect-src 'none'",
    "frame-src 'none'",
    "worker-src 'none'",
]
FORBIDDEN_CSP_TOKENS = ["'unsafe-inline'", "'unsafe-eval'", "data:", "http:"]
FORBIDDEN_TAGS = {"script", "form", "iframe", "object", "embed"}
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
                for token in FORBIDDEN_CSP_TOKENS:
                    if token in parser.csp:
                        errors.append(f"{rel}: CSP contains forbidden token {token}")

            if parser.referrer != "no-referrer":
                errors.append(f"{rel}: referrer policy must be no-referrer")

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

    public_suffixes = {".html", ".md", ".css", ".xml", ".txt", ".py", ".yml", ".yaml"}
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
        if rel != Path("scripts/site_audit.py"):
            for pattern in ATTRIBUTION_PATTERNS:
                if pattern.search(text):
                    errors.append(f"{rel}: private-build attribution marker detected")

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
    print("Active content: none")
    print("Inline event handlers/styles: none")
    print("Local references: OK")
    print("CSP/referrer policy: OK")
    print("XML: OK")
    print("security.txt: OK")
    print("Public identity/research records: OK")


if __name__ == "__main__":
    main()
