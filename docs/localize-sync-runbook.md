# Localize Sync Runbook

Use this runbook for production zh-Hant sync.

## Operating Model

The latest translation state is governed by Localize/Weblate. The Git
translation repository mirrors that state so maintainers can review generated
trees, build translated KM bundles, and keep reproducible history.

Normal automation is one-way:

```text
Localize/Weblate -> GitHub translation repository
```

## Secrets

Scheduled sync and alignment do not need Weblate write access. Configure
`LOCALIZE_API_TOKEN` in the production translation repository only when the
read-only status workflow should use authenticated Weblate checks. If it is not
configured, the check report uses anonymous access. See
[Security and Permissions](security-and-permissions.md).

## Scheduled Pull Sync

The external translation workflow should run:

- on a schedule, usually twice per day
- on pull requests targeting `master`
- on manual `workflow_dispatch`

The workflow runs [`src/sync_from_localize.py`][sync-from-localize-py]. That
command:

1. Downloads the current Weblate PO to `sources/localize/zh_Hant/latest.po`.
2. Writes the previous checked-in `latest.po` to a temporary comparison file.
3. Force-refreshes `tree/` from the latest Weblate PO.
4. Rebuilds `builds/final_translated.po`.
5. Rebuilds `builds/final_translated.km`.
6. Refreshes review outputs.
7. Commits and pushes only when tracked files changed.

Scheduled runs commit directly to `master` when repository policy allows it.
Pull request runs write only to same-repository branches. Fork pull requests
skip writer commits.

For a local maintainer run against a checked-out translation repository, use:

```shell
make repo-sync TRANSLATION_REPO_DIR=/path/to/dsw-root-locales-zh_Hant
```

Set `TRANSLATION_REPO_DIR` as described in the
[Command Reference](command-reference.md). The target is
declared in the [`Makefile`][makefile].

## Read-Only Status and Alignment Reports

Use the status report workflow to inspect Weblate PO health without changing
Git or Weblate. It:

1. Checks out the translation repository.
2. Pulls the latest Weblate PO into the ephemeral workflow checkout.
3. Runs [`src/report_localize_status.py`][report-localize-status-py].
4. Writes a GitHub step summary and uploads
   `reviews/localize_status_report.json` and
   `reviews/localize_status_report.md` as artifacts.

The status report includes Weblate review-state counts from the PO export as
part of current translation health.

The same workflow can also run
[`src/report_weblate_checks.py`][report-weblate-checks-py] with the Weblate query
`has:check`. That catches website-side quality-check warnings that are not
always visible from PO state alone. The check report is diagnostic and uses
`--allow-api-failure` so Weblate API rate limits are captured in the report
while Git sync monitoring continues.

It requires only `contents: read`.

Use the alignment report workflow to verify output consistency without
changing Git or Weblate. It:

1. Downloads the latest Weblate PO into a temporary file.
2. Compares it with `sources/localize/zh_Hant/latest.po`.
3. Rebuilds `builds/final_translated.po` from `tree/`.
4. Rebuilds `builds/final_translated.km` from the final PO and configured KM
   metadata.
5. Uploads JSON, Markdown, and generated comparison artifacts.

The alignment report is allowed to fail when drift is detected. That failure
means a pull sync, tree rebuild, or KM rebuild should run before maintainers
trust the repository outputs. It also requires only `contents: read` and does
not change translations.

To run the same alignment check from your machine, use:

```shell
make repo-align TRANSLATION_REPO_DIR=/path/to/dsw-root-locales-zh_Hant
```

## Merge Gate Behavior

Before a same-repository branch reaches `master`, the pull request writer pulls
Weblate again and refreshes the branch. This makes the merge candidate include
the latest website translation state.

Use forward commits for sync and workflow corrections on public branches.

## Conflict Policy

Normal sync is Weblate-first:

- Weblate entries that are ready for use win.
- Checked-in tree translations that differ from Weblate are replaced during
  force-refresh.
- Entries marked for review stay in Weblate for translators to resolve on the
  website.

## KM Updates

The current production policy is latest-only. Use
[KM Update Runbook](km-update-runbook.md) when the DSW Registry publishes a new
Common DSW KM.

## Troubleshooting

- If sync commits nothing, Weblate and Git outputs are already aligned.
- If `translation-config.yml` fails validation, fix config before running sync.
- If tree parsing fails in CI, the writer may restore malformed files from the
  tracking branch once and retry.
- If Weblate has untranslated strings after sync, check whether they are empty,
  marked for review, or missing from the current KM source.

[report-localize-status-py]: https://github.com/ThreeMonth03/DSW-KM-translation-tool/blob/master/src/report_localize_status.py
[report-weblate-checks-py]: https://github.com/ThreeMonth03/DSW-KM-translation-tool/blob/master/src/report_weblate_checks.py
[sync-from-localize-py]: https://github.com/ThreeMonth03/DSW-KM-translation-tool/blob/master/src/sync_from_localize.py
[makefile]: https://github.com/ThreeMonth03/DSW-KM-translation-tool/blob/master/Makefile
