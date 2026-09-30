# Handoff Checklist

Use this page when handing repository maintenance to another maintainer.

## Operating Model

- Translate in Localize/Weblate or submit a reviewed Markdown pull request.
- Let GitHub Actions mirror Weblate into this repository.
- Review generated `tree/`, `builds/`, and `reviews/` files in Git.
- Use workflow reports to diagnose drift before editing repository files.

## Repositories

| Repository | Purpose |
| --- | --- |
| This repository | Formal {{TARGET_LANGUAGE_LABEL}} translation mirror and build output |
| [`{{TOOLING_REPOSITORY}}`](https://github.com/{{TOOLING_REPOSITORY}}) | Tooling used by workflows and local maintenance commands |

## Required Access

- Write access to this translation repository.
- Access to repository Actions and workflow logs.
- Access to configure repository Actions secrets.
- Localize/Weblate account for translation review.

## Secrets

Configure these secrets in this repository:

| Secret | Used by | Purpose |
| --- | --- | --- |
| `LOCALIZE_API_TOKEN` | `github_translation_import.yml`, `localize_status_report.yml` | Import accepted GitHub translation edits and read Weblate quality-check units |
| `DSW_REGISTRY_TOKEN` | `km_version_auto_update.yml` | Download newer published KM bundles |

## Workflow Inventory

| Workflow | Schedule | Writes | Normal Result |
| --- | --- | --- | --- |
| `localize_auto_sync.yml` | Scheduled | Git | Mirrors Weblate; commits only when tracked files changed |
| `github_translation_import.yml` | Push to the tracking branch, manual | Weblate, then Git if sync changes follow | Imports accepted GitHub translation edits after merge; fails on conflicts |
| `localize_status_report.yml` | Scheduled, manual | No | Reports empty translations, review-state counts, and Weblate checks |
| `localize_alignment_report.yml` | Scheduled, manual | No | Verifies Weblate PO, checked-in PO, tree, and final PO alignment |
| `km_version_auto_update.yml` | Scheduled, manual | Git | No-ops when current; updates only after validation passes |
| `validate_translation_config.yml` | Push, PR, manual, daily | Test DSW only | Validates config, scaffold and PR edits; reports source gaps and PO coverage; checks browser import |
| `release.yml` | Successful sync/import/KM update, or manual retry | GitHub Release | Publishes changed, verified native PO assets and provenance |

## Routine Check

1. Check the latest `localize_auto_sync.yml` run.
2. Check the latest `localize_alignment_report.yml` run.
3. Check the latest `localize_status_report.yml` run.
4. Check the latest `km_version_auto_update.yml` run.
5. Check the latest `validate_translation_config.yml` source and native locale reports.
6. If a report failed, read its job summary and logs before changing files.
   Request a full report with `upload_report` on a manual run if needed.

See [Maintenance Runbook](maintenance-runbook.md) for commands.

## Expected Outcomes

- Sync reports Git and Weblate are already aligned, or creates one sync commit.
- Alignment report status is `aligned`.
- Status report accurately lists official empty and fuzzy translations.
- KM auto-update reports `current`, or commits an update after validation passes.

Weblate sync continues when the available KM is older. Source differences and
incomplete coverage are informational; invalid PO files, broken reproducibility
and actual DSW import failures still block CI.

## Failure Entry Points

| Symptom | First Place to Look |
| --- | --- |
| Sync failed | `localize_auto_sync.yml` log |
| Git and Weblate drifted | Alignment workflow job summary |
| Weblate checks changed | Status workflow job summary |
| KM update failed | KM auto-update workflow job summary |
| Config validation failed | `translation-config.yml` and `validate_translation_config.yml` log |
| Translation PR failed | KM Translation Operations job summary |
| Native import failed | Job log and `native-dsw-review` failure diagnostics |
| Coverage is incomplete or resource pages remain untranslated | Job summary; enable `upload_review` for the full review bundle |
| Shared source POT differs | Source-catalog job summary; enable `upload_review` for snapshots |

## Local Maintenance

Use a disposable checkout for local sync or KM repair. The sync command can
commit and push from the checkout where it runs.

Use [Maintenance Runbook](maintenance-runbook.md#local-checks) for local
commands.
