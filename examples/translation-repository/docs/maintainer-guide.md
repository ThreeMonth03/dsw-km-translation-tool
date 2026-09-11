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
- Same-repository pull requests expand canonical shared-block translations into
  their referenced tree fields before translation reporting; fork pull requests
  remain read-only.
- Pull requests that do not edit translation text can be refreshed from Weblate
  before merge.
- Pull requests that edit `tree/**/translation.md` are reported for review and
  imported to Weblate only after merge when they do not conflict with Weblate
  edits to the same entries.
- Read-only reports check Weblate status and repository alignment.
- Config validation also checks that managed docs and workflows match the
  tooling templates rendered from this repository's config.
- KM auto-update tracks newer published DSW Registry KM bundles when validation
  passes.

## Publish to DSW

After repository CI passes, download `builds/final_translated.po`. In DSW, open
the matching source Knowledge Model version, choose its locale import action,
enter the locale name, and upload the PO. Confirm that DSW reports the expected
language and review a questionnaire that uses that Knowledge Model.

The source `.km` under `sources/knowledge-models/` exists only for validation.
Do not import it as a translated Knowledge Model.

## Actions Secrets

Configure these Actions repository secrets:

- `LOCALIZE_API_TOKEN`: used by the GitHub translation import workflow and by
  the read-only Weblate checks report. The checks report can still run without
  it, but API limits may be stricter.
- `DSW_REGISTRY_TOKEN`: used when KM auto-update downloads a newer Registry
  bundle.

See [Security and Permissions](security-and-permissions.md) for the workflow
permission matrix.
