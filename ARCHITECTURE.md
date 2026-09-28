# THOR-SEC Architecture

## Hosts

| Role | URL | Notes |
| --- | --- | --- |
| Canonical | https://codethor0.github.io/thor-sec/ | GitHub Pages, built from `main`. All canonical links, the sitemap, the feed, and `security.txt` use this host. |
| Mirror | https://thor-sec.codethor0.workers.dev/ | Cloudflare Workers Static Assets. Serves `_headers` security headers and `X-Robots-Tag: noindex`. |

No custom domain is in use. GitHub Pages is never redirected to the mirror.

## Deployment

- GitHub Pages deploys automatically from `main`.
- The Cloudflare mirror deploys only through `scripts/cloudflare-staging-deploy.sh`, run manually from a clean, fast-forwarded checkout. The script writes a local checkpoint bundle, runs `scripts/site_audit.py`, exports tracked files with `git archive`, removes non-public files, refuses to deploy if anything outside the public allowlist remains, deploys, and then verifies public pages, private-path 404s, security headers, and the absence of script tags.
- No Git-connected automatic build exists for the Cloudflare mirror.

## Security invariants

- Static-first. Pages are plain HTML and CSS.
- No client-side JavaScript: `script-src 'none'`, `connect-src 'none'`, and no `<script>` tags.
- No cookies, browser analytics, advertising trackers, or visitor counters.
- No third-party runtime assets. The Inter typeface is self-hosted in `assets/fonts/` under the SIL Open Font License 1.1.
- `form-action 'none'`, `object-src 'none'`, `frame-src 'none'`, `worker-src 'none'`, `frame-ancestors 'none'` (mirror header).
- `Referrer-Policy: no-referrer` everywhere.
- HSTS is not set by this repository.
- CI (`.github/workflows/site-check.yml`) runs the fail-closed static audit on every push and pull request.

## Public and private boundary

Only public site files are served. Repository internals and tooling (`.git`, `.github`, `scripts`, `worker`, `README.md`, `SECURITY.md`, `ARCHITECTURE.md`, `LICENSE`, `wrangler.jsonc`, `.assetsignore`, `.gitignore`, `.nojekyll`) are excluded from the Cloudflare upload by `.assetsignore` and by the deploy script's allowlist, and the deploy script verifies they return 404.

## Planned exception

A single research-request endpoint, `POST /api/request`, may be added to the Cloudflare mirror as the only server-side logic. It would receive a plain HTML form (no JavaScript), validate every field server-side, accept no file uploads, retain no visitor telemetry, and forward accepted requests to a private intake queue. This endpoint is not live; until it is, research requests use the email link on the commission page.

## Payment boundary

THOR-SEC never collects or processes payment data. Commissioned research is paid through an external Stripe invoice or payment link only after a written scope and fee are agreed. The research-support links are separate from commissioned work.

## Data minimization

Initial contact must not include secrets, credentials, customer data, exploit code, or confidential logs. Sensitive material is exchanged only after a channel is agreed for an accepted engagement.

## Rollback

Each change is a single commit on `main` that can be reverted with a normal `git revert`. History is never rewritten. Local checkpoint bundles are kept outside the repository. GitHub Pages remains available as the canonical site if the mirror is taken down.
