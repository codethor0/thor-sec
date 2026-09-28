#!/usr/bin/env bash
# One-shot end-to-end check of the /api/request intake on the Cloudflare mirror.
# Files exactly one clearly labeled self-test request, confirms the private issue
# holds no visitor telemetry, closes it, and confirms the honeypot files nothing.
# Requires: curl, gh (logged in as codethor0), jq.
set -euo pipefail

API="https://thor-sec.codethor0.workers.dev/api/request"
REPO="codethor0/thor-sec-intake"
ORIGIN="https://codethor0.github.io"
MARK="THOR-SEC SELF-TEST $(date -u +%Y%m%dT%H%M%SZ)"

die() { printf '[FAIL] %s\n' "$*" >&2; exit 1; }
ok()  { printf '    [ok] %s\n' "$*"; }
post() {
  curl -q -sS --max-time 20 -o /dev/null -w '%{http_code} %{redirect_url}' -X POST \
    -H "Origin: $ORIGIN" -H 'Content-Type: application/x-www-form-urlencoded' "$@" "$API"
}
open_count() { gh issue list -R "$REPO" --state open --limit 100 --json number --jq 'length'; }

for t in curl gh jq; do command -v "$t" >/dev/null 2>&1 || die "missing tool: $t"; done
[ "$(gh api user --jq .login)" = "codethor0" ] || die "gh is not logged in as codethor0"

before="$(open_count)"
out="$(post --data-urlencode "website=bot" --data-urlencode "name=honeypot" \
  --data-urlencode "email=selftest@example.org" --data-urlencode "question=honeypot" \
  --data-urlencode "authorization=planning" --data-urlencode "confirm=yes")"
[ "${out%% *}" = "303" ] || die "honeypot expected 303, got $out"
sleep 3
[ "$(open_count)" = "$before" ] || die "honeypot submission created an issue"
ok "honeypot: generic 303, no issue filed"

out="$(post --data-urlencode "name=$MARK" --data-urlencode "email=selftest@example.org" \
  --data-urlencode "organization=THOR-SEC" --data-urlencode "question=$MARK: end-to-end intake check" \
  --data-urlencode "authorization=planning" --data-urlencode "publication=private" \
  --data-urlencode "notes=Automated self-test. No action needed." --data-urlencode "confirm=yes")"
code="${out%% *}"; loc="${out#* }"
[ "$code" = "303" ] || die "self-test expected 303, got $code (503 means the secret or repo is not set up)"
[ "$loc" = "https://codethor0.github.io/thor-sec/request-received.html" ] || die "unexpected redirect: $loc"
ok "self-test accepted (303 to request-received.html)"

sleep 3
num="$(gh issue list -R "$REPO" --state open --search "\"$MARK\" in:body" --json number --jq '.[0].number // empty')"
[ -n "$num" ] || die "self-test issue not found in $REPO"
[ "$(open_count)" = "$((before + 1))" ] || die "expected exactly one new issue"
body="$(gh issue view "$num" -R "$REPO" --json body --jq .body)"
if printf '%s' "$body" | grep -Eqi 'user-agent|cf-connecting-ip|x-forwarded|cookie|authorization: bearer|token'; then
  die "issue #$num contains telemetry or credential-like text; left open for review"
fi
ok "issue #$num contains no IP, User-Agent, cookie, or token data"
gh issue close "$num" -R "$REPO" --comment "Automated self-test; closing." >/dev/null
ok "issue #$num closed"
echo
echo "INTAKE SELF-TEST PASSED"
