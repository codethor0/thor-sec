#!/usr/bin/env bash
# THOR-SEC Cloudflare staging deploy (workers.dev only).
#
# What this does, in order:
#   1. Verifies the local repository (path, origin, branch, clean tracked tree).
#   2. Writes a checkpoint bundle under ~/Projects/thor-sec-checkpoints/.
#   3. Fast-forwards to origin/main (never resets, never force-pushes).
#   4. Runs the static security audit.
#   5. Exports tracked files with git archive into a temp directory, strips
#      everything that is not a public asset, and fails if anything else remains.
#   6. Deploys that export with Wrangler (static assets plus the single
#      /api/request intake Worker; no other server-side code).
#   7. Verifies the live workers.dev URL: pages, 404 handling, blocked paths,
#      security headers, and absence of script tags.
#
# Usage:
#   cloudflare-staging-deploy.sh                full run (steps 1-7)
#   cloudflare-staging-deploy.sh --verify-only  step 7 only, no changes made
#
# What this never does: change DNS, custom domains, canonical URLs, HSTS,
# GitHub Pages, or any other Cloudflare zone. No tokens are read or printed;
# authentication uses the existing Wrangler OAuth login.

set -euo pipefail

REPO="${THOR_SEC_REPO:-$HOME/Projects/thor-sec-public-site}"
CHECKPOINT_ROOT="$HOME/Projects/thor-sec-checkpoints"
EXPECTED_URL="https://thor-sec.codethor0.workers.dev"
WRANGLER="wrangler@4.142.0"
VERIFY_ONLY=0
case "${1:-}" in
  "") ;;
  --verify-only) VERIFY_ONLY=1 ;;
  *) printf 'unknown argument: %s\n' "$1" >&2; exit 2 ;;
esac

PAGES="/ /research.html /work.html /about.html /inventions.html /security.html /now.html /request-received.html /robots.txt /sitemap.xml /feed.xml /styles.css /.well-known/security.txt /assets/thor-thor-profile.webp /assets/fonts/InterVariable.woff2 /assets/thor-sec-social-card.png /assets/favicon.png /assets/apple-touch-icon.png"
BLOCKED="/.git/config /.git/HEAD /.github/CODEOWNERS /scripts/site_audit.py /scripts/cloudflare-staging-deploy.sh /worker/intake.mjs /worker/intake.test.mjs /wrangler.jsonc /.assetsignore /.gitignore /README.md /SECURITY.md /ARCHITECTURE.md /LICENSE /_headers"

say()  { printf '\n==> %s\n' "$*"; }
ok()   { printf '    [ok] %s\n' "$*"; }
die()  { printf '\n[FAIL] %s\n' "$*" >&2; exit 1; }

WORK_DIR=""
cleanup() { if [ -n "$WORK_DIR" ] && [ -d "$WORK_DIR" ]; then rm -rf "$WORK_DIR"; fi; }
trap cleanup EXIT

# curl -q (first argument) ignores ~/.curlrc so local defaults such as --fail
# cannot change status handling.
curlq() { curl -q -sS --max-time 20 "$@"; }

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
url="$EXPECTED_URL"
head_sha="n/a"
checkpoint_dir="n/a"

if [ "$VERIFY_ONLY" -eq 0 ]; then
# ---------------------------------------------------------------- 1. preflight
say "Preflight"
for tool in git python3 curl npx tar; do
  command -v "$tool" >/dev/null 2>&1 || die "required tool not found: $tool"
done
ok "tools present"

[ -d "$REPO/.git" ] || die "repository not found at $REPO (set THOR_SEC_REPO to override)"
cd "$REPO"

origin_url="$(git remote get-url origin)"
case "$origin_url" in
  https://github.com/codethor0/thor-sec|https://github.com/codethor0/thor-sec.git|git@github.com:codethor0/thor-sec.git) ;;
  *) die "unexpected origin remote: $origin_url" ;;
esac
ok "origin is codethor0/thor-sec"

branch="$(git rev-parse --abbrev-ref HEAD)"
[ "$branch" = "main" ] || die "current branch is '$branch'; switch to main first"
ok "on main"

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  git status --short --untracked-files=no
  die "tracked files have uncommitted changes; commit or stash them first"
fi
ok "tracked tree clean"

# -------------------------------------------------------------- 2. checkpoint
say "Checkpoint"
checkpoint_dir="$CHECKPOINT_ROOT/cf-staging-$stamp"
mkdir -p "$checkpoint_dir"
git bundle create "$checkpoint_dir/thor-sec.bundle" --all >/dev/null 2>&1
git rev-parse HEAD > "$checkpoint_dir/HEAD.txt"
git bundle verify "$checkpoint_dir/thor-sec.bundle" >/dev/null 2>&1 || die "checkpoint bundle failed verification"
ok "bundle written to $checkpoint_dir"

# ------------------------------------------------------------ 3. fast-forward
say "Sync with origin/main (fast-forward only)"
git fetch --quiet origin main
pre_sync="$(git rev-parse HEAD)"
if ! git merge --ff-only --quiet origin/main; then
  die "local main has diverged from origin/main; resolve manually (nothing was changed)"
fi
# Bash keeps executing the copy it started with, so restart once if the sync
# just replaced this script; otherwise stale checks would run on new content.
if [ -z "${THOR_SEC_RESTARTED:-}" ] && ! git diff --quiet "$pre_sync" HEAD -- scripts/cloudflare-staging-deploy.sh; then
  ok "deploy script updated by sync; restarting with the new version"
  exec env THOR_SEC_RESTARTED=1 bash "$REPO/scripts/cloudflare-staging-deploy.sh"
fi
head_sha="$(git rev-parse --short HEAD)"
ok "at $head_sha"

for f in wrangler.jsonc .assetsignore _headers 404.html index.html; do
  [ -f "$f" ] || die "required file missing after sync: $f"
done
ok "wrangler.jsonc, .assetsignore, _headers present"

# ------------------------------------------------------------------- 4. audit
say "Static security audit"
python3 scripts/site_audit.py

# ------------------------------------------------------------------ 5. export
say "Build clean export from git (tracked files only, no .git)"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/thor-sec-deploy.XXXXXX")"
SITE="$WORK_DIR/site"
mkdir -p "$SITE"
git archive --format=tar HEAD | tar -x -C "$SITE"

rm -rf "$SITE/.github" "$SITE/scripts"
rm -f "$SITE"/worker/*.test.mjs
rm -f "$SITE/README.md" "$SITE/SECURITY.md" "$SITE/ARCHITECTURE.md" "$SITE/LICENSE" "$SITE/.gitignore" "$SITE/.nojekyll"

unexpected=""
while IFS= read -r rel; do
  case "$rel" in
    ./*.html|./styles.css|./robots.txt|./sitemap.xml|./feed.xml|./_headers) ;;
    ./.well-known/security.txt) ;;
    ./assets/*.jpg|./assets/*.webp|./assets/*.png|./assets/*.svg) ;;
    ./assets/fonts/*.woff2|./assets/fonts/LICENSE-Inter.txt) ;;
    ./wrangler.jsonc|./.assetsignore|./worker/intake.mjs) ;;
    *) unexpected="$unexpected $rel" ;;
  esac
done < <(cd "$SITE" && find . -type f)
[ -z "$unexpected" ] || die "export contains non-public files:$unexpected"
[ ! -e "$SITE/.git" ] || die "export contains .git"
main_entry="$(sed -n 's/^[[:space:]]*"main"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$SITE/wrangler.jsonc")"
[ "$main_entry" = "worker/intake.mjs" ] || die "wrangler.jsonc must declare exactly worker/intake.mjs as Worker code"
ok "export contains public assets only ($(cd "$SITE" && find . -type f | wc -l | tr -d ' ') files)"

# ------------------------------------------------------------------ 6. deploy
say "Cloudflare authentication"
cd "$SITE"
whoami_out="$(npx --yes "$WRANGLER" whoami 2>&1 || true)"
if ! printf '%s\n' "$whoami_out" | grep -Eqi "you are logged in"; then
  echo "    Not logged in. A browser window will open for Cloudflare OAuth."
  npx --yes "$WRANGLER" login
fi
ok "wrangler authenticated"

say "Deploy to workers.dev (static assets + /api/request intake)"
deploy_log="$WORK_DIR/deploy.log"
if ! npx --yes "$WRANGLER" deploy 2>&1 | tee "$deploy_log"; then
  die "wrangler deploy failed (see output above)"
fi

url="$(grep -Eo 'https://thor-sec\.[a-z0-9-]+\.workers\.dev' "$deploy_log" | head -n 1 || true)"
[ -n "$url" ] || url="$EXPECTED_URL"
ok "deployed: $url"
cd "$REPO"
fi

# ------------------------------------------------------------------ 7. verify
say "Verify live site"
code_for() { curlq -L -o /dev/null -w '%{http_code}' "$1" 2>/dev/null || true; }

# A fresh workers.dev deployment can answer inconsistently for a short time
# while it propagates. Each public URL is retried for up to 3 minutes.
wait_for_200() {
  local target="$1" n=0 c
  while :; do
    c="$(code_for "$target")"
    [ "$c" = "200" ] && { echo "200"; return 0; }
    n=$((n + 1))
    [ "$n" -lt 36 ] || { echo "$c"; return 1; }
    sleep 5
  done
}

failures=0
fail() { printf '    [FAIL] %s\n' "$*"; failures=$((failures + 1)); }

echo "    waiting for the deployment to settle (up to 3 minutes per URL)"
for p in $PAGES; do
  if c="$(wait_for_200 "$url$p")"; then ok "200 $p"; else fail "$c $p (expected 200)"; fi
done

c="$(code_for "$url/this-page-does-not-exist-$stamp")"
if [ "$c" = "404" ]; then ok "404 for missing page"; else fail "$c for missing page (expected 404)"; fi

for p in $BLOCKED; do
  c="$(code_for "$url$p")"
  if [ "$c" = "404" ]; then ok "404 $p (not public)"; else fail "$c $p (expected 404, must not be public)"; fi
done

headers="$(curlq -L -D - -o /dev/null "$url/" || true)"
check_header() {
  if printf '%s\n' "$headers" | grep -Eiq "$1"; then ok "header: $2"; else fail "header missing or wrong: $2"; fi
}
check_header "^content-security-policy:.*script-src 'none'.*frame-ancestors 'none'" "Content-Security-Policy"
check_header "^referrer-policy: *no-referrer" "Referrer-Policy"
check_header "^x-content-type-options: *nosniff" "X-Content-Type-Options"
check_header "^x-frame-options: *deny" "X-Frame-Options"
check_header "^permissions-policy:" "Permissions-Policy"
check_header "^cross-origin-opener-policy: *same-origin" "Cross-Origin-Opener-Policy"
check_header "^x-permitted-cross-domain-policies: *none" "X-Permitted-Cross-Domain-Policies"
check_header "^x-robots-tag: *noindex" "X-Robots-Tag (mirror not indexed)"

# Intake endpoint: only rejection paths are exercised; no request is filed.
api="$url/api/request"
c="$(curlq -o /dev/null -w '%{http_code}' "$api" 2>/dev/null || true)"
if [ "$c" = "405" ]; then ok "405 GET /api/request"; else fail "$c GET /api/request (expected 405)"; fi
c="$(curlq -o /dev/null -w '%{http_code}' -X POST -H 'Origin: https://attacker.invalid' -H 'Content-Type: application/x-www-form-urlencoded' --data 'name=x' "$api" 2>/dev/null || true)"
if [ "$c" = "403" ]; then ok "403 untrusted Origin"; else fail "$c untrusted Origin (expected 403)"; fi
c="$(curlq -o /dev/null -w '%{http_code}' -X POST -H 'Origin: https://codethor0.github.io' -H 'Content-Type: application/json' --data '{}' "$api" 2>/dev/null || true)"
if [ "$c" = "415" ]; then ok "415 wrong content type"; else fail "$c wrong content type (expected 415)"; fi
c="$(curlq -o /dev/null -w '%{http_code}' -X POST -H 'Origin: https://codethor0.github.io' -H 'Content-Type: application/x-www-form-urlencoded' --data 'name=' "$api" 2>/dev/null || true)"
if [ "$c" = "400" ]; then ok "400 missing required fields"; else fail "$c missing required fields (expected 400)"; fi

script_failures=0
for p in / /research.html /work.html /about.html /inventions.html /security.html /now.html /request-received.html; do
  body="$(curlq -L "$url$p" || true)"
  if [ -z "$body" ]; then fail "empty body for $p"; script_failures=1; continue; fi
  if printf '%s\n' "$body" | grep -qi "<script"; then fail "script tag found on $p"; script_failures=1; fi
done
[ "$script_failures" -ne 0 ] || ok "no script tags on any page"

# ------------------------------------------------------------------ report
say "Report"
echo "    Commit deployed : $head_sha"
echo "    Staging URL     : $url"
echo "    Checkpoint      : $checkpoint_dir"
echo "    Production      : https://codethor0.github.io/thor-sec/ (unchanged)"
echo "    DNS / canonical / HSTS : unchanged"
if [ "$failures" -ne 0 ]; then
  echo
  echo "    Re-check without redeploying:"
  echo "      bash scripts/cloudflare-staging-deploy.sh --verify-only"
  die "$failures verification check(s) failed. To take staging down: npx --yes $WRANGLER delete thor-sec"
fi
echo
echo "STAGING DEPLOY VERIFIED"
echo "Optional hardening when finished: npx --yes $WRANGLER logout"
