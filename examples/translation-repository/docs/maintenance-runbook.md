# Maintenance Runbook

Use this runbook for routine operation of a Common DSW Knowledge Model
translation repository.

## Daily Health Check

Check the latest scheduled Weblate-to-Git sync:

```shell
gh run list --workflow localize_auto_sync.yml --branch master --limit 5
```

Healthy outcomes:

- Git was already aligned with Weblate.
- The workflow committed a Weblate sync update to `master`.

Check read-only reports:

```shell
gh run list --workflow localize_status_report.yml --branch master --limit 5
gh run list --workflow localize_alignment_report.yml --branch master --limit 5
```

Check KM auto-update:

```shell
gh run list --workflow km_version_auto_update.yml --branch master --limit 5
```

## Manual Triggers

Trigger Weblate-to-Git sync after a translation batch lands in Weblate:

```shell
gh workflow run localize_auto_sync.yml --ref master
```

Trigger read-only reports:

```shell
gh workflow run localize_status_report.yml --ref master
gh workflow run localize_alignment_report.yml --ref master
```

Trigger KM auto-update immediately:

```shell
gh workflow run km_version_auto_update.yml --ref master
```

## KM and Config Updates

Normal Weblate sync does not refresh `translation-config.yml`. The KM
auto-update workflow may update only the active KM version and bundle path after
the newer KM bundle, Weblate mirror, rebuild, validation, and alignment checks
all pass. Other settings, such as branch names, Weblate URLs, and tooling refs,
are maintained manually.

## Local Checks

Use the tooling repository for local checks:

```shell
TOOL_REPO_DIR=/path/to/dsw-km-translation-tool
TRANSLATION_REPO_DIR=/path/to/translation-repo

cd "$TOOL_REPO_DIR"
make install-dev
make repo-validate TRANSLATION_REPO_DIR="$TRANSLATION_REPO_DIR"
make repo-align TRANSLATION_REPO_DIR="$TRANSLATION_REPO_DIR"
```

Writer targets such as `make repo-sync` and `make repo-km-update` may commit and
push from the checkout where they run. Use them only from a disposable checkout
or when you intentionally want a Git update.

## Troubleshooting

- Sync created no commit: Git is already aligned with Weblate.
- Alignment failed: download `localize-alignment-report` and compare the
  generated files with the checked-in files.
- Generated KM changed unexpectedly: compare `sources/localize/*/latest.po`
  with `builds/final_translated.po`.
- KM auto-update failed before downloading a bundle: check `DSW_REGISTRY_TOKEN`.
- KM auto-update failed after rebuilding: inspect the validation or alignment
  error.
