# {{TARGET_LANGUAGE_LABEL}} translation of {{SOURCE_KM_ID}}

This repository is the Git-authoritative {{TARGET_LANGUAGE_LABEL}} translation
of `{{SOURCE_KM_ID}}`. It intentionally has no Weblate dependency.

Current source:

- repository: `{{SOURCE_REPOSITORY}}`
- commit: `{{SOURCE_REF}}`
- bundle: `{{SOURCE_BUNDLE_PATH}}`
- KM version: `{{SOURCE_VERSION}}`

The complete source commit and bundle path are pinned in
`translation-config.yml`. Translators edit only Translation blocks in
`tree/**/translation.md`. `sources/`, `builds/`, and generated tree metadata are
maintained by the DSW KM Translation Tool.

Import `builds/final_translated.po` into the source Knowledge Model through
DSW's locale import. The `.km` file under `sources/knowledge-models/` is used
only to validate locale references. Pull-request CI also publishes a 14-day
`{{LOCALE_ASSET_STEM}}-<commit SHA>` review artifact. Versioned, long-term
downloads are GitHub Release assets named
`{{LOCALE_ASSET_STEM}}-<KM version>-r<revision>.po`.

CI checks out the exact source commit, refreshes the source KM snapshot,
rebuilds the translation tree and native locale PO, and requires a clean Git
diff. Use this mode for a mutable review branch; switch to an immutable GitHub
Release dependency when the source KM is formally released.

See [docs/maintenance.md](docs/maintenance.md) for bootstrap, update, and
release-cutover commands.
