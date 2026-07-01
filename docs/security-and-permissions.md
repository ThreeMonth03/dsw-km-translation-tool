# Security and Permissions

Use this page when configuring GitHub Actions, repository settings, or secrets
for a production translation repository.

## Source of Truth

Latest zh-Hant translation text is governed by Localize/Weblate. The Git
translation repository is a reproducible mirror for automation, review, and
visual inspection.

Scheduled automation may pull from Weblate into Git. Scheduled automation must
not push from Git to Weblate.

## Required Workflow Permissions

| Workflow | GitHub permission | Secrets | Writes translations? |
| --- | --- | --- | --- |
| Localize auto sync | `contents: write` | none | Writes Git only |
| Localize status report | `contents: read` | none | No |
| Localize alignment report | `contents: read` | none | No |
| Reviewed migration to Weblate | `contents: read` | `LOCALIZE_API_TOKEN` only when applying | Writes Weblate only after manual apply |

The auto-sync writer currently supports direct commits to the tracking branch.
If branch protection prevents direct writer pushes, keep Weblate as the source
of truth and switch to one of these equivalent strategies:

- grant a narrow bot exception for the sync workflow; or
- have CI open/update a sync pull request and enable auto-merge.

Both strategies preserve the same policy: Weblate changes flow into Git without
manual translation editing in Git.

## Secret Placement

`LOCALIZE_API_TOKEN` belongs in the production translation repository that runs
the manual reviewed migration workflow. For the public zh-Hant repository, that
means:

```text
depositar/dsw-root-locales-zh_Hant
```

Do not store Localize/Weblate tokens in this tooling repository unless this
repository itself is running an apply workflow. The normal sync, status, and
alignment workflows do not need that secret.

## Token Handling

- Never commit tokens into `translation-config.yml`, workflow files, logs, or
  generated reports.
- Prefer GitHub Actions secrets over local shell history.
- Use the token only with `migrate_reviewed_to_localize.py --apply`.
- Dry-run migration without a token first and review
  `reviews/localize_migration_report.json`.

## Branch Protection and History

Do not rewrite public `master` history to clean up intermediate automation
commits. Use forward commits for workflow or generated-artifact corrections.

If GitHub branch-protection APIs are unavailable or return not-found responses
for the current account, rely on observed workflow behavior and repository
settings visible to maintainers. Direct scheduled sync commits are acceptable
only while repository settings allow them.
