# First-Time Maintainer Guide

Use this page when you need to understand the repository before changing code
or operating a translation sync.

## Mental Model

For production zh-Hant work, Localize/Weblate owns the latest translation text.
This tooling turns that website state into files that can be reviewed, tested,
and committed in Git:

```text
Localize/Weblate PO -> tree/ -> final PO -> translated KM -> Git commit
```

The tooling repository contains reusable code, tests, workflow templates, and
documentation. A dedicated translation repository contains the actual
translation config and generated translation artifacts.

## First Hour

1. Read [Architecture](architecture.md) to learn which layer owns each
   behavior.
2. Read [Command Reference](command-reference.md) to identify whether a command
   is read-only or writes generated files.
3. Read the relevant runbook before touching production automation:
   [Localize Sync Runbook](localize-sync-runbook.md) for Weblate-to-Git sync, or
   [KM Update Runbook](km-update-runbook.md) for source KM updates.
4. Set up the tooling repo locally:

   ```shell
   make install-dev
   make test
   make docs
   ```

5. When changing behavior, find the thin CLI script in `src/*.py`, then follow
   it into `src/dsw_translation_tool/` for the reusable implementation.

## Safe vs. Writing Commands

Use read-only commands while getting oriented. They are enough to validate a
checkout, inspect Weblate status, and confirm artifact alignment.

Read-only report commands inspect state and write only report files in the
current checkout. They do not upload to Weblate and do not push Git commits
unless a workflow explicitly does so.

Writer commands rebuild translation artifacts and may commit/push when run by
the configured GitHub Actions workflow. Before changing a writer, read its
runbook and its tests.

The [Command Reference](command-reference.md) marks common external-repository
commands by safety level.

## Where Changes Usually Belong

| Change | Start Here | Tests |
| --- | --- | --- |
| Tree format, shared strings, PO/KM output | `workflow.py`, `tree.py`, `sync.py`, `knowledge_model_service.py` | `tests/translation/` |
| Weblate download, merge, sync commit behavior | `localize_sync.py`, `localize_merge.py`, `repository_ci_sync.py`, `ci_sync.py` | `tests/infra/` |
| Translation repository config rules | `translation_repository_config.py` | `tests/infra/` |
| KM Registry discovery or guarded KM updates | `km_registry.py`, `km_bundle_sync.py`, `km_latest_sync.py` | `tests/infra/` |
| Workflow wiring | `examples/github-actions/` templates first | `tests/infra/test_github_workflows.py` |

If the right place is unclear, add or adjust a small test that describes the
behavior you expect. The module ownership usually becomes obvious from there.
