# Security and Permissions

Use this page when configuring GitHub Actions, secrets, and workflow
permissions for this repository.

## Workflow Permission Matrix

| Workflow | Permission | Secret | Writes |
| --- | --- | --- | --- |
| `localize_auto_sync.yml` | `contents: write` | none | tracking branch or same-repository PR branch |
| `localize_status_report.yml` | `contents: read` | optional `LOCALIZE_API_TOKEN` | nothing |
| `localize_alignment_report.yml` | `contents: read` | none | nothing |
| `km_version_auto_update.yml` | `contents: write` | `DSW_REGISTRY_TOKEN` only when a newer KM exists | tracking branch only after validation |
| `validate_translation_config.yml` | `contents: read` | none | nothing |

## Actions Secrets

Configure these Actions repository secrets:

```text
LOCALIZE_API_TOKEN
DSW_REGISTRY_TOKEN
```

`LOCALIZE_API_TOKEN` is used only by the status report for read-only Weblate
checks. The report falls back to anonymous access if the token is unavailable,
but API limits may be stricter.

`DSW_REGISTRY_TOKEN` is used only by KM auto-update when it needs to download a
newly published source KM bundle.

## Token Hygiene

- Keep tokens out of `translation-config.yml`, workflow YAML, logs, and
  generated reports.
