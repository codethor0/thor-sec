# THOR-SEC

Independent security research lab and public website for Thor Thor.

**Mission:** THOR-SEC finds hard security and infrastructure problems, develops original solutions, and publishes the evidence that they work.

**Live site:** https://codethor0.github.io/thor-sec/

## Research Identity

- **Researcher:** Thor Thor
- **ORCID:** https://orcid.org/0009-0001-6573-385X
- **Featured publication:** Mission-Invariant Architecture Morphing (MIAM), version 1.0.0
- **DOI:** https://doi.org/10.5281/zenodo.23001045
- **Source and reproducibility artifacts:** https://github.com/codethor0/miam

## Selected Research Projects

- **llm-agent-control-plane:** https://github.com/codethor0/llm-agent-control-plane
- **Model Identity Verifier:** https://github.com/codethor0/model-identity-verifier
- **BoundaryLayer:** https://github.com/codethor0/boundary-layer
- **Impact Forecast Algorithm (IFA):** https://github.com/codethor0/impact-forecast
- **Security Stack Engineering (SSE):** https://github.com/codethor0/security-stack-engineering

## Site Architecture

THOR-SEC uses a static-first publication model:

- No client-side JavaScript
- One plain HTML research-request form on the commission page (no JavaScript, no uploads), posted to a single validating endpoint
- No cookies or analytics
- Self-hosted Inter typeface (SIL OFL 1.1); no third-party fonts or runtime assets
- Same-origin CSS and images
- Restrictive meta Content Security Policy
- `no-referrer` browser policy
- Public `security.txt` and vulnerability disclosure policy
- CI security audit on every push to main and every pull request targeting main
- Light and dark themes follow the visitor's device setting; no stored preference

Hosting:

- **Canonical:** GitHub Pages at https://codethor0.github.io/thor-sec/. Canonical URLs, the sitemap, the feed, and `security.txt` all point here.
- **Mirror:** Cloudflare Workers Static Assets at https://thor-sec.codethor0.workers.dev/, deployed only through `scripts/cloudflare-staging-deploy.sh`. The mirror applies the response headers in `_headers`, serves only public assets (see `.assetsignore`), and sends `X-Robots-Tag: noindex` so it does not compete with the canonical site.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design and security invariants.

Public indexes:

- **Research archive:** https://codethor0.github.io/thor-sec/research.html
- **Case studies:** https://codethor0.github.io/thor-sec/case-studies.html
- **Commission research:** https://codethor0.github.io/thor-sec/work.html
- **About:** https://codethor0.github.io/thor-sec/about.html
- **Patents & inventions:** https://codethor0.github.io/thor-sec/inventions.html
- **Site security & privacy:** https://codethor0.github.io/thor-sec/security.html
- **RSS/Atom:** https://codethor0.github.io/thor-sec/feed.xml

## Purpose

THOR-SEC is a static public website for open-source defensive cybersecurity research, AI security work, cybersecurity writing, and security engineering projects. Views and research are personal. THOR-SEC is not affiliated with, endorsed by, or representative of any employer.

## Publishing research

Papers are recorded once, in `scripts/research.json`. `scripts/build_research.py` turns that record into static files: a page per paper under `research/` (with Google Scholar citation tags, DOI, status, limitations, and a citation block), the latest-research list on the home page, the papers list on the research archive, `feed.xml`, and `sitemap.xml`.

```bash
python3 scripts/build_research.py          # rewrite the built files
python3 scripts/build_research.py --check  # CI: fail if any built file is out of date
```

Edit only the JSON and rerun the script; do not hand-edit text between `<!-- build:... -->` markers.

## Local Preview

```bash
cd thor-sec
python3 -m http.server 8080
```

Open http://localhost:8080 in your browser.

## GitHub Pages Deployment

1. Create a GitHub repository named `thor-sec` under the `codethor0` account.
2. Push the contents of this directory to the repository root.
3. In the repository settings, go to **Pages**.
4. Under **Build and deployment**, set **Source** to **Deploy from a branch**.
5. Select the `main` branch and the `/ (root)` folder.
6. Save. The site will be available at https://codethor0.github.io/thor-sec/ after deployment completes.

## Responsible Use

THOR-SEC supports authorized defensive security work only. Research and tools are intended for systems, applications, accounts, networks, and data that are owned, operated, or explicitly authorized for testing or analysis.

See [SECURITY.md](SECURITY.md) for vulnerability disclosure guidance.

## License

MIT License. See [LICENSE](LICENSE).
