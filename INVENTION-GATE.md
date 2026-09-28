# THOR-SEC Invention Publication Gate

This repository is public. It must never become the private invention inventory.

The invention gate separates internal invention decisions from public disclosure. Before any invention or invention-like technical mechanism is added to the public Inventions page, it must be classified into exactly one of these states:

1. **file-first** - do not publish enabling details until filing strategy and disclosure timing are resolved.
2. **keep-private** - do not publish the invention or enough detail to reconstruct it.
3. **publish-intentionally** - public disclosure is an explicit decision and a stable public record may be listed.
4. **ownership-unresolved** - hard stop. Do not publish until ownership, employment, collaboration, or other rights questions are resolved.

## Public-repository rule

Only `publish-intentionally` records are allowed in `scripts/invention_publications.json`.

The public registry contains only information that is already approved for intentional public disclosure. It must not contain:

- private invention titles or descriptions;
- filing plans that are not already public;
- ownership disputes or unresolved ownership analysis;
- confidential employer or collaborator information;
- unpublished claim language, prototypes, diagrams, or enabling implementation details;
- notes about inventions classified as `file-first`, `keep-private`, or `ownership-unresolved`.

Those non-public decisions belong in a private record outside this repository.

## Publication workflow

To add an item to the public Inventions page:

1. Make the invention decision outside this public repository.
2. If the decision is anything other than `publish-intentionally`, stop.
3. If ownership is unresolved, stop.
4. If filing strategy requires pre-publication confidentiality, stop.
5. For an intentional disclosure, create or identify the stable public record.
6. Add only the approved public metadata to `scripts/invention_publications.json`.
7. Run `python3 scripts/build_inventions.py`.
8. Run the full site audit and CI-equivalent checks.
9. Review the generated disclosure before committing.

CI runs `python3 scripts/build_inventions.py --check` and fails if `inventions.html` drifts from the public disclosure registry or if the registry contains a non-public decision state.

## Patent-status language

The public site must not describe an item as patented, patent-pending, filed, granted, or otherwise assigned a legal status unless that statement is intentionally public and supported by an appropriate public identifier.

A defensive publication or public implementation is a public record; it does not by itself establish patentability, patent ownership, or a patent license.

This is a publication-control policy, not legal advice.
