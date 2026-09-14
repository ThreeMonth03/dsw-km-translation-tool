# Security and Permissions

Use this page when configuring GitHub Actions, secrets, and workflow
permissions for this repository.

## Workflow Permission Matrix

| Workflow | Permission | Secret | Writes |
| --- | --- | --- | --- |
| `localize_auto_sync.yml` | `contents: write` | none | tracking branch from trusted scheduled runs |
| `github_translation_import.yml` | `contents: write` | `LOCALIZE_API_TOKEN` | Weblate after merge; Git only when sync changes follow |
| `localize_status_report.yml` | `contents: read` | optional `LOCALIZE_API_TOKEN` | nothing |
| `localize_alignment_report.yml` | `contents: read` | none | nothing |
| `km_version_auto_update.yml` | `contents: write` | `DSW_REGISTRY_TOKEN` only when a newer KM exists | tracking branch only after validation |
| `validate_translation_config.yml` | `contents: read` | none | disposable test DSW only; no repository or production writes |
| `release.yml` | `contents: write` | none | Creates a locale revision after sync and validation on the tracking branch |

The workflows that write `master` or Weblate share the
`translation-state-master` concurrency group with `cancel-in-progress: false`.
Keep both settings aligned so an active writer job is not cancelled by a later
run.

Pull-request validation runs in `validate_translation_config.yml` with
read-only repository permission and no secrets. It compares the exact pull
request head with its recorded base commit, uploads the translation report,
and builds a PO preview in its temporary checkout. Canonical shared edits are
expanded automatically. It never writes to the branch or Weblate.
Native import checks create isolated DSW containers bound only to loopback,
using disposable test users. They remove containers and volumes afterwards.
No production DSW URL, account or token is used. Artifacts contain PO coverage
and screenshots, not authentication state.
The upstream source audit reads the configured public GitHub repository without
credentials and retains a POT snapshot for review. It does not execute upstream
code, push commits, create PRs or change Weblate source strings or settings.

## Actions Secrets

Configure these Actions repository secrets:

```text
LOCALIZE_API_TOKEN
DSW_REGISTRY_TOKEN
```

`LOCALIZE_API_TOKEN` is required by the post-merge GitHub translation import
workflow. It is also used by the status report for read-only Weblate checks;
that report falls back to anonymous access if the token is unavailable, but API
limits may be stricter.

`DSW_REGISTRY_TOKEN` is used only by KM auto-update when it needs to download a
newly published source KM bundle.

## Token Hygiene

- Keep tokens out of `translation-config.yml`, workflow YAML, logs, and
  generated reports.
