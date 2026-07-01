# Localize Sync Runbook

Use this runbook for production zh-Hant sync and one-shot migration work.

## Operating Model

The latest translation state is governed by Localize/Weblate. The Git
translation repository mirrors that state so maintainers can review generated
trees, build translated KM bundles, and keep reproducible history.

Normal automation is one-way:

```text
Localize/Weblate -> GitHub translation repository
```

Repository-to-Weblate upload is not scheduled. Use it only for migration,
emergency repair, or an explicit maintainer decision that reviewed Git content
must be pushed to Weblate first.

## Scheduled Pull Sync

The external translation workflow should run:

- on a schedule, usually twice per day
- on pull requests targeting `master`
- on manual `workflow_dispatch`

The workflow runs `src/sync_from_localize.py`. That command:

1. Downloads the current Weblate PO to `sources/localize/zh_Hant/latest.po`.
2. Keeps the previous snapshot as `sources/localize/zh_Hant/base.po`.
3. Force-refreshes `tree/` from the latest Weblate PO.
4. Rebuilds `builds/final_translated.po`.
5. Rebuilds `builds/final_translated.km`.
6. Refreshes review outputs.
7. Commits and pushes only when tracked files changed.

Scheduled runs commit directly to `master` when repository policy allows it.
Pull request runs write only to same-repository branches. Fork pull requests
skip writer commits.

## Merge Gate Behavior

Before a same-repository branch reaches `master`, the pull request writer pulls
Weblate again and refreshes the branch. This makes the merge candidate include
the latest website translation state.

If branch protection blocks direct writer pushes, keep the same policy but
switch the workflow to open or update an auto-merged sync pull request. The
user-facing result should still be that Git mirrors Weblate without manual
translation review in Git.

## Conflict Policy

Normal sync is Weblate-first:

- Non-fuzzy Weblate changes win.
- Checked-in tree translations that differ from Weblate are replaced during
  force-refresh.
- Fuzzy or needs-editing translations stay in Weblate for translators to
  resolve on the website.

Do not reintroduce chapter protection for normal daily sync. Reviewed chapter
protection was a migration tool, not the steady-state policy.

## One-Shot Repository-To-Weblate Migration

Use `src/migrate_reviewed_to_localize.py` only when reviewed Git translations
are ahead of Weblate and must be uploaded.

Dry-run first:

```shell
.venv/bin/python src/migrate_reviewed_to_localize.py \
  --repo-root /path/to/translation-repo \
  --config translation-config.yml \
  --chapters 0004 0005 0006 \
  --fill-localize-blanks-from-repo
```

Review:

```text
reviews/localize_migration_upload.po
reviews/localize_migration_report.json
```

Apply only after human review:

```shell
LOCALIZE_API_TOKEN=... \
.venv/bin/python src/migrate_reviewed_to_localize.py \
  --repo-root /path/to/translation-repo \
  --config translation-config.yml \
  --chapters 0004 0005 0006 \
  --fill-localize-blanks-from-repo \
  --apply
```

After upload, run the normal scheduled pull sync or trigger the sync workflow
manually. Weblate becomes authoritative again immediately after migration.

## KM Updates

The current production policy is latest-only. When the DSW Registry publishes a
new Common DSW KM:

1. Download the published KM bundle into `sources/knowledge-models/`.
2. Update `translation-config.yml` to point at the new bundle and supported
   version.
3. Run config validation.
4. Run Localize pull sync against a disposable branch first.
5. Review source mismatch or missing-entry reports before merging.

Do not add unpublished versions such as draft `2.8.0` bundles.

## Troubleshooting

- If sync commits nothing, Weblate and Git artifacts are already aligned.
- If `translation-config.yml` fails validation, fix config before running sync.
- If tree parsing fails in CI, the writer may restore malformed files from the
  tracking branch once and retry.
- If Weblate upload returns authorization errors, check the
  `LOCALIZE_API_TOKEN` secret and account permissions.
- If Weblate has untranslated strings after sync, check whether they are empty,
  fuzzy, needs-editing, or missing from the current KM source.
