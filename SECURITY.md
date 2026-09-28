# Security Policy

## Scope

THOR-SEC is an independent open-source cybersecurity research portfolio. This repository contains static website content and defensive cybersecurity research materials. It is intended for authorized defensive security work only.

## Reporting a Vulnerability

If you discover a security issue related to this repository or its published content, contact:

**Email:** [codethor@gmail.com](mailto:codethor@gmail.com)

Do not send secrets, credentials, customer data, exploit code, private logs, or confidential information in the first message. Do not submit sensitive data through public GitHub issues.

## What to Include

Vulnerability reports should include:

- The affected URL or file
- A clear description of the issue
- The potential impact
- Safe reproduction steps, if applicable
- Any suggested remediation, if known

Provide only the detail needed for responsible disclosure.

## Response

Reports will be reviewed and acknowledged as promptly as possible. THOR-SEC does not operate a formal bug bounty program.

## Responsible Use

Research and tools associated with THOR-SEC are intended for systems, applications, accounts, networks, and data that are owned, operated, or explicitly authorized for testing or analysis. Unauthorized access, credential theft, phishing, data exfiltration, malware deployment, denial-of-service activity, sabotage, and any activity intended to cause harm are not supported.


## Website Security Boundary

The public THOR-SEC site is intentionally static. It does not require client-side JavaScript, forms, cookies, analytics, third-party fonts, or third-party runtime assets.

The repository applies a restrictive meta Content Security Policy and a no-referrer policy. The canonical site is hosted on GitHub Pages, where repository content cannot configure every HTTP response header. A mirror on Cloudflare Workers Static Assets additionally serves the response headers defined in `_headers`. The public source and CI checks are the auditable repository security boundary. See ARCHITECTURE.md for details.
