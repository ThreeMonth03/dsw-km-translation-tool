# Common DSW Knowledge Model Translation

This repository mirrors a Localize/Weblate translation of the Common DSW
Knowledge Model into Git for automation and review.

Make routine translation changes in Localize/Weblate, then let automation sync
them here. Reviewed GitHub pull requests may also change translation text in
`tree/**/translation.md` or canonical shared Translation blocks; after merge,
automation imports safe edits back to Weblate. No local build is required.
See [Contributing translations](docs/contributing.md) for browser-only steps.

Download the PO from this repository's **Releases → Latest**. The working copy
is `builds/final_translated.po`. Import the PO into the
matching source Knowledge Model version with DSW's locale import; no separate
Knowledge Model package is created.

This workflow requires DSW 4.33 or newer.

For maintenance details, start with [docs/README.md](docs/README.md).
