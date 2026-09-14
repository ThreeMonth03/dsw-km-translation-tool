# Maintainer Guide

This repository is the automation and visualization workspace for one Common
DSW Knowledge Model translation.

The latest translation state is governed by Localize/Weblate. GitHub stores a
reviewable mirror of that state plus a native DSW locale PO.

Operational details are split into:

- [Sync Policy](sync-policy.md)
- [Maintenance Runbook](maintenance-runbook.md)
- [Security and Permissions](security-and-permissions.md)

## Repository Layout

```text
translation-config.yml
sources/knowledge-models/
sources/localize/
tree/
builds/
reviews/
```

- `translation-config.yml` defines the KM, language, branch, Weblate, Registry,
  and tooling settings for this repository.
  Configuration schema 3 derives artifact paths from KM coordinates and rejects
  unknown fields.
- `sources/knowledge-models/` stores released source KM bundles.
- `sources/localize/` stores the latest Weblate PO snapshot.
- `tree/` stores the generated translation tree mirrored from Weblate.
- `builds/final_translated.po` is regenerated from the tree and imported into
  DSW as a Knowledge Model locale.
- `reviews/` stores generated review outputs and workflow reports.

## Operating Model

Normal translation work happens in Localize/Weblate. Automation then mirrors the
website state into this repository:

- Scheduled sync pulls Weblate into Git.
- All pull requests resolve canonical shared-block edits in memory for reporting
  and expand them only in a temporary checkout for the PO preview. They never
  write to the branch or Weblate.
- Pull requests that edit translation Markdown are reported for review and
  imported to Weblate only after merge when they do not conflict with Weblate
  edits to the same entries.
- Read-only reports check Weblate status and repository alignment.
- Daily native verification reports shared POT source gaps separately from
  translation coverage; see [Shared Source Catalog](sync-policy.md#shared-source-catalog).
- Config validation also checks that managed docs and workflows match the
  tooling templates rendered from this repository's config.
- KM auto-update tracks newer published DSW Registry KM bundles when validation
  passes.

## Publish to DSW

Download a PO from this repository's **Releases → Latest**. In DSW, open
the desired Knowledge Model version, open **Locales → Import**,
enter the locale name, and upload the PO. Confirm that DSW reports the expected
language. In a test project's **Settings**, select the imported **Language** and
save before reviewing its **Questionnaire**. See the
[PO review instructions](contributing.md#review-the-po) for the full procedure.

The `.km` under `sources/knowledge-models/` supplies context and browser tests.
Catalog and KM versions need not match: only matching source strings translate;
unmatched strings remain in the source language.
Do not import it as a translated Knowledge Model.

Use [Publishing a locale](maintenance-runbook.md#publishing-a-locale) to create
a new translation release. Pull-request artifacts are temporary review files.

## Actions Secrets

Configure these Actions repository secrets:

- `LOCALIZE_API_TOKEN`: used by the GitHub translation import workflow and by
  the read-only Weblate checks report. The checks report can still run without
  it, but API limits may be stricter.
- `DSW_REGISTRY_TOKEN`: used when KM auto-update downloads a newer Registry
  bundle.

See [Security and Permissions](security-and-permissions.md) for the workflow
permission matrix.
