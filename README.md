# THOR-SEC

Independent defensive cybersecurity research portfolio and public website for Thor Thor.

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
- No forms
- No cookies or analytics
- No third-party fonts or runtime assets
- Same-origin CSS and images
- Restrictive meta Content Security Policy
- `no-referrer` browser policy
- Public `security.txt` and vulnerability disclosure policy
- CI security audit on every push and pull request
- Cloudflare Pages response-header policy in `_headers`, inactive until deployed through Cloudflare Pages

Cloudflare deployment is staged separately from the current GitHub Pages production site. The canonical site URL, sitemap, `security.txt`, and public links remain on GitHub Pages until a Cloudflare custom domain has been verified end to end.

Public indexes:

- **Research archive:** https://codethor0.github.io/thor-sec/research.html
- **Commission research:** https://codethor0.github.io/thor-sec/work.html
- **About:** https://codethor0.github.io/thor-sec/about.html
- **Patents & inventions:** https://codethor0.github.io/thor-sec/inventions.html
- **Site security & privacy:** https://codethor0.github.io/thor-sec/security.html
- **RSS/Atom:** https://codethor0.github.io/thor-sec/feed.xml

## Purpose

THOR-SEC is a static public website for open-source defensive cybersecurity research, AI security work, cybersecurity writing, and security engineering projects. Views and research are personal. THOR-SEC is not affiliated with, endorsed by, or representative of any employer.

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
