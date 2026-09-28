#!/usr/bin/env python3
# Builds the public THOR-SEC inventions list from intentional disclosures only.
#
# The public registry is NOT a private invention inventory. Only records whose
# decision is exactly "publish-intentionally" may exist here.
#
# Usage:
#   python3 scripts/build_inventions.py
#   python3 scripts/build_inventions.py --check

from __future__ import annotations

from html import escape
from pathlib import Path
from urllib.parse import urlparse
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "scripts/invention_publications.json"
DATA = json.loads(DATA_PATH.read_text(encoding="utf-8"))
ENTRIES = DATA["entries"]

ALLOWED_DECISION = "publish-intentionally"
ENTRY_KEYS = {
    "id", "title", "year", "tag", "record_type", "url", "summary", "decision"
}
FORBIDDEN_PRIVATE_STATES = {"file-first", "keep-private", "ownership-unresolved"}


def h(value: str) -> str:
    return escape(str(value), quote=False).replace('"', "&quot;")


def validate() -> None:
    seen = set()
    if not isinstance(ENTRIES, list) or not ENTRIES:
        raise SystemExit("invention_publications.json: at least one public disclosure is required")

    for entry in ENTRIES:
        keys = set(entry)
        if keys != ENTRY_KEYS:
            missing = sorted(ENTRY_KEYS - keys)
            extra = sorted(keys - ENTRY_KEYS)
            parts = []
            if missing:
                parts.append("missing=" + ",".join(missing))
            if extra:
                parts.append("extra=" + ",".join(extra))
            raise SystemExit(f"{entry.get('id', '<unknown>')}: registry schema mismatch ({'; '.join(parts)})")

        item_id = entry["id"]
        if not re.fullmatch(r"[a-z0-9-]+", item_id):
            raise SystemExit(f"{item_id}: invalid id")
        if item_id in seen:
            raise SystemExit(f"duplicate disclosure id: {item_id}")
        seen.add(item_id)

        if entry["decision"] != ALLOWED_DECISION:
            raise SystemExit(
                f"{item_id}: public registry accepts only {ALLOWED_DECISION}; "
                "non-public decisions must stay outside this repository"
            )

        combined = " ".join(str(v) for v in entry.values()).lower()
        leaked = sorted(state for state in FORBIDDEN_PRIVATE_STATES if state in combined)
        if leaked:
            raise SystemExit(
                f"{item_id}: public registry contains non-public decision state(s): {', '.join(leaked)}"
            )

        if not re.fullmatch(r"\d{4}", entry["year"]):
            raise SystemExit(f"{item_id}: year must be YYYY")
        parsed = urlparse(entry["url"])
        if parsed.scheme != "https" or not parsed.netloc:
            raise SystemExit(f"{item_id}: public record URL must be absolute HTTPS")
        for field in ("title", "tag", "record_type", "summary"):
            if not str(entry[field]).strip():
                raise SystemExit(f"{item_id}: {field} must not be empty")


def disclosure_block() -> str:
    out = ['        <ol class="entry-list">']
    for entry in ENTRIES:
        out += [
            f'          <li class="entry" data-disclosure-id="{h(entry["id"])}">',
            f'            <p class="entry-meta">{h(entry["year"])} &middot; <span class="tag">{h(entry["tag"])}</span> &middot; {h(entry["record_type"])}</p>',
            f'            <h3><a href="{h(entry["url"])}">{h(entry["title"])}</a></h3>',
            f'            <p>{h(entry["summary"])}</p>',
            '          </li>',
        ]
    out.append("        </ol>")
    return "\n".join(out) + "\n"


def replace_block(text: str, name: str, body: str, path: str) -> str:
    start = f"<!-- build:{name}:start -->"
    end = f"<!-- build:{name}:end -->"
    pattern = re.compile(re.escape(start) + r".*?" + r"([ \t]*)" + re.escape(end), re.S)
    match = pattern.search(text)
    if not match:
        raise SystemExit(f"{path}: build markers for '{name}' not found")
    indent = match.group(1)
    return text[:match.start()] + start + "\n" + body + indent + end + text[match.end():]


def expected_output() -> str:
    target = ROOT / "inventions.html"
    current = target.read_text(encoding="utf-8")
    return replace_block(current, "public-disclosures", disclosure_block(), "inventions.html")


def main() -> None:
    validate()
    check = "--check" in sys.argv[1:]
    target = ROOT / "inventions.html"
    expected = expected_output()
    current = target.read_text(encoding="utf-8")

    if current == expected:
        if check:
            print(f"INVENTION GATE UP TO DATE ({len(ENTRIES)} intentional public disclosure(s))")
        else:
            print("Wrote 0 invention output(s): already up to date")
        return

    if check:
        print("INVENTION GATE OUT OF DATE")
        print("- inventions.html does not match scripts/invention_publications.json")
        raise SystemExit(1)

    target.write_text(expected, encoding="utf-8")
    print(f"Wrote inventions.html ({len(ENTRIES)} intentional public disclosure(s))")


if __name__ == "__main__":
    main()
