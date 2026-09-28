# THOR-SEC Architecture

## Hosts

| Role | URL | Notes |
| --- | --- | --- |
| Canonical | https://codethor0.github.io/thor-sec/ | GitHub Pages, built from `main`. All canonical links, the sitemap, the feed, and `security.txt` use this host. |
| Mirror | https://thor-sec.codethor0.workers.dev/ | Cloudflare Workers Static Assets. Serves `_headers` security headers and `X-Robots-Tag: noindex`. |

No custom domain is in use. GitHub Pages is never redirected to the mirror.

## Deployment

- GitHub Pages deploys automatically from `main`.
- The Cloudflare mirror deploys only through `scripts/cloudflare-staging-deploy.sh`, run manually from a clean, fast-forwarded checkout. The script writes a local checkpoint bundle, runs `scripts/site_audit.py`, exports tracked files with `git archive`, removes non-public files, refuses to deploy if anything outside the public allowlist remains, deploys, and then verifies public pages, private-path 404s, security headers, the absence of script tags, and that the intake endpoint rejects bad methods, origins, content types, and incomplete submissions.
- No Git-connected automatic build exists for the Cloudflare mirror.

## Security invariants

- Static-first. Pages are plain HTML and CSS.
- No client-side JavaScript: `script-src 'none'`, `connect-src 'none'`, and no `<script>` tags.
- No cookies, browser analytics, advertising trackers, or visitor counters.
- No third-party runtime assets. The Inter typeface is self-hosted in `assets/fonts/` under the SIL Open Font License 1.1.
- `form-action 'none'` on every page except `work.html`, whose policy allows only the intake endpoint host and the canonical host (for the post-submit redirect); `object-src 'none'`, `frame-src 'none'`, `worker-src 'none'`, `frame-ancestors 'none'` (mirror header).
- `Referrer-Policy: no-referrer` everywhere.
- HSTS is not set by this repository.
- CI (`.github/workflows/site-check.yml`) runs the fail-closed static audit on every push to main and every pull request targeting main.
- `main` is protected by a repository ruleset: no deletion or force pushes, linear history only, and every commit must carry a GitHub-verified signature.

## Public and private boundary

The repository is public, and GitHub Pages publishes it as-is, so nothing in it is secret. The Cloudflare mirror serves only public site files: repository internals and tooling (`.git`, `.github`, `scripts`, `worker`, `README.md`, `SECURITY.md`, `ARCHITECTURE.md`, `LICENSE`, `wrangler.jsonc`, `.assetsignore`, `.gitignore`, `.nojekyll`) are excluded from the Cloudflare upload by `.assetsignore` and by the deploy script's allowlist, and the deploy script verifies they return 404.

## Research-request intake

The only server-side logic is `worker/intake.mjs`, which runs on the Cloudflare mirror for exactly one path, `POST /api/request` (`run_worker_first`). Every other path is served from static assets.

- Input: the plain HTML form on `work.html`, `application/x-www-form-urlencoded` only, 24 KiB maximum, no file uploads.
- Checks, in order: method, `Origin` (the canonical host or the mirror host only), content type, size, native rate limit (5 requests per 60 seconds for the endpoint as a whole), hidden honeypot field, then strict server-side validation of every field against fixed lengths and allowed values.
- Output: an accepted request becomes an issue in the private repository `codethor0/thor-sec-intake`, and the browser is sent a 303 redirect to `request-received.html` on the canonical host. Submitted text is fenced and has `@` mentions and `#` references neutralized.
- Credential: a fine-grained GitHub token limited to issues on that one repository, stored only as the Cloudflare secret `INTAKE_GITHUB_TOKEN`. It is never committed. If it is missing, the endpoint fails closed with a generic 503.
- Not recorded: visitor IP address, User-Agent, location, cookies, or raw request headers. Worker observability and logging are disabled.
- Errors return generic plain-text messages that point to the email fallback. The email link on the commission page always remains available.
- Trade-off: the rate limit is global to the endpoint, so a burst of abusive traffic can temporarily delay legitimate submissions; email remains the fallback.
- Tests: `node --test worker/intake.test.mjs` runs in CI.

## Payment boundary

THOR-SEC never collects or processes payment data. Commissioned research is paid through an external Stripe invoice or payment link only after a written scope and fee are agreed. The research-support links are separate from commissioned work.

## Data minimization

Initial contact must not include secrets, credentials, customer data, exploit code, or confidential logs. Sensitive material is exchanged only after a channel is agreed for an accepted engagement.

## Rollback

Each change is a single commit on `main` that can be reverted with a normal `git revert`. History is never rewritten. Local checkpoint bundles are kept outside the repository. GitHub Pages remains available as the canonical site if the mirror is taken down.
