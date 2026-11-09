# Contributing to THOR-SEC

This repository is the source of the THOR-SEC independent security research site. Contributions are welcome when they fix something concrete.

## In scope

- Broken links, typos, rendering problems, and accessibility issues on the site.
- Factual corrections to published research summaries, with a citation to the paper, dataset, or source that supports the correction.
- Fixes to the build and audit scripts or the intake Worker, with tests.

Out of scope: new pages, redesigns, analytics, third-party scripts, and changes to published papers. Papers are versioned on Zenodo. A correction to a paper is made in a new version there, not in this repository.

## Reporting

- Site bugs and research corrections: open an issue with the page URL, what is wrong, and the evidence.
- Security vulnerabilities: do not open a public issue. Follow [SECURITY.md](../SECURITY.md).
- Never include credentials, customer data, private research material, or exploit code in an issue or pull request.

## Running the checks

The checks need Python 3 and Node.js and make no network requests. Run them before opening a pull request.

```sh
python3 scripts/site_audit.py
python3 scripts/build_research.py --check
python3 scripts/build_case_studies.py --check
python3 scripts/build_inventions.py --check
node --test worker/intake.test.mjs
git diff --check
```

Generated pages come from the JSON files in `scripts/`. Edit the data, run the matching build script without `--check`, and commit the regenerated pages. Do not hand-edit generated HTML.

## Pull requests

- One focused change per pull request, with a short description of what changed and why.
- No client-side JavaScript, external scripts, remote fonts, or tracking. The Content Security Policy stays as strict as it is.
- Claims must match their sources. Keep what was observed separate from what is inferred.
- `main` is protected. Pull requests merge only after the Site Check workflow passes and the maintainer approves.

Contributions are licensed under the MIT License in [LICENSE](../LICENSE).
