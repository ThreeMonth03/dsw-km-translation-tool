# Common DSW Knowledge Model Translation

This repository mirrors a Localize/Weblate translation of the Common DSW
Knowledge Model into Git for automation and review.

Make routine translation changes in Localize/Weblate, then let automation sync
them here. Reviewed GitHub pull requests may also fill empty translation fields in
`tree/**/translation.md` or canonical shared Translation blocks; after merge,
automation imports safe edits back to Weblate. No local build is required.
Review may refine those new translations within the same PR. Leave existing
nonempty translations unchanged, including fuzzy entries; report suspected
errors separately for a maintainer's decision.
See [Contributing translations](docs/contributing.md) for browser-only steps.

Changed usable translations are released automatically after sync and validation.
Download the PO from this repository's **Releases → Latest**. The working copy
is `builds/final_translated.po`. Import the PO into the
desired Knowledge Model version with DSW's locale import; no separate
Knowledge Model package is created.

This workflow requires DSW 4.33 or newer. Catalog and KM versions need not match:
DSW translates matching source text; unmatched strings stay in the source language.
Official Weblate/POT changes are mirrored without waiting for a new KM.

For maintenance details, start with [docs/README.md](docs/README.md).
