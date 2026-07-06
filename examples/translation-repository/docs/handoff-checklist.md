# Handoff Checklist

Use this page when handing repository maintenance to another maintainer.

## Operating Model

- Translate in Localize/Weblate.
- Let GitHub Actions mirror Weblate into this repository.
- Review generated `tree/`, `builds/`, and `reviews/` files in Git.
- Use workflow reports to diagnose drift before editing repository files.

## Required Access

- Write access to this translation repository.
- Access to repository Actions and workflow logs.
- Access to configure repository Actions secrets.
- Localize/Weblate account for translation review.

## Secrets

Configure these repository secrets:

| Secret | Used by | Purpose |
| --- | --- | --- |
| `LOCALIZE_API_TOKEN` | `localize_status_report.yml` | Read Weblate quality-check units |
| `DSW_REGISTRY_TOKEN` | `km_version_auto_update.yml` | Download newer published KM bundles |

## Workflow Inventory

| Workflow | Writes | Normal Result |
| --- | --- | --- |
| `localize_auto_sync.yml` | Git | Mirrors Weblate; commits only when tracked files changed |
| `localize_status_report.yml` | No | Reports empty translations, review-state counts, and Weblate checks |
| `localize_alignment_report.yml` | No | Verifies Weblate PO, checked-in PO, tree, final PO, and final KM alignment |
| `km_version_auto_update.yml` | Git | No-ops when current; updates only after validation passes |
| `validate_translation_config.yml` | No | Validates `translation-config.yml` |

## Routine Check

1. Check the latest `localize_auto_sync.yml` run.
2. Check the latest `localize_alignment_report.yml` run.
3. Check the latest `localize_status_report.yml` run.
4. Check the latest `km_version_auto_update.yml` run.
5. If a report failed, download its artifact before changing files.
