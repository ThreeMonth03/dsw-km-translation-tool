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

## Read-Only Status and Alignment Reports

Use the status report workflow to inspect Weblate PO health without changing
Git or Weblate. It:

1. Checks out the translation repository.
2. Pulls the latest Weblate PO into the ephemeral workflow checkout.
3. Runs `src/report_localize_status.py`.
4. Writes a GitHub step summary and uploads
   `reviews/localize_status_report.json` and
   `reviews/localize_status_report.md` as artifacts.

Weblate exports entries that need editing through the PO `fuzzy` flag. The
status report lists all fuzzy entries as current review items; it does not keep
a separate exception baseline.

The same workflow can also run `src/report_weblate_checks.py` with the Weblate
query `has:check`. That catches website-side quality-check warnings that are
not always visible from PO fuzzy flags alone. The check report is diagnostic and
should use `--allow-api-failure` so Weblate API rate limits do not block Git
sync monitoring.

It requires only `contents: read` and does not use `LOCALIZE_API_TOKEN`.

Use the alignment report workflow to verify artifact consistency without
changing Git or Weblate. It:

1. Downloads the latest Weblate PO into a temporary file.
2. Compares it with `sources/localize/zh_Hant/latest.po`.
3. Rebuilds `builds/final_translated.po` from `tree/`.
4. Rebuilds `builds/final_translated.km` from the final PO and configured KM
   metadata.
5. Uploads JSON, Markdown, and generated comparison artifacts.

The alignment report is allowed to fail when drift is detected. That failure
means a pull sync, tree rebuild, or KM rebuild should run before maintainers
trust the repository artifacts. It also requires only `contents: read` and does
not use `LOCALIZE_API_TOKEN`.

## Merge Gate Behavior

Before a same-repository branch reaches `master`, the pull request writer pulls
Weblate again and refreshes the branch. This makes the merge candidate include
the latest website translation state.

If branch protection blocks direct writer pushes, keep the same policy but
switch the workflow to open or update an auto-merged sync pull request. The
user-facing result should still be that Git mirrors Weblate without manual
translation review in Git.

Do not rewrite public `master` to compress earlier automation commits. Once
published, sync and workflow corrections should be forward-only commits unless
repository maintainers explicitly coordinate a history rewrite.

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

The current production policy is latest-only. Use
[KM Update Runbook](km-update-runbook.md) when the DSW Registry publishes a new
Common DSW KM.

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
