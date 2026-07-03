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

5. When changing behavior, find the thin CLI script in [`src/*.py`][src-root],
   then follow it into [`src/dsw_translation_tool/`][package-dir] for the
   reusable implementation.

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

## Common Change Paths

Use these paths to find the first module and test area for a change. For a
complete ownership map, see [Architecture](architecture.md).

### Translation Tree or Generated PO/KM Output

Start with:

- [`src/dsw_translation_tool/workflow.py`][workflow-py]
- [`src/dsw_translation_tool/tree.py`][tree-py]
- [`src/dsw_translation_tool/sync.py`][sync-py]
- [`src/dsw_translation_tool/knowledge_model_service.py`][knowledge-model-service-py]

Test with:

- [`tests/translation/`][tests-translation]

### Shared Strings

Start with:

- [`src/dsw_translation_tool/shared_blocks.py`][shared-blocks-py]
- [`src/sync_shared_strings.py`][sync-shared-strings-py]

Test with:

- [`tests/translation/test_shared_string_sync.py`][test-shared-string-sync-py]
- [`tests/infra/test_cli_sync.py`][test-cli-sync-py]

### Weblate Download, Merge, or Sync Commits

Start with:

- [`src/dsw_translation_tool/localize_sync.py`][localize-sync-py]
- [`src/dsw_translation_tool/localize_merge.py`][localize-merge-py]
- [`src/dsw_translation_tool/repository_ci_sync.py`][repository-ci-sync-py]
- [`src/dsw_translation_tool/ci_sync.py`][ci-sync-py]

Test with:

- [`tests/infra/test_localize_sync.py`][test-localize-sync-py]
- [`tests/infra/test_localize_merge.py`][test-localize-merge-py]
- [`tests/infra/test_ci_sync.py`][test-ci-sync-py]

### Translation Repository Config

Start with:

- [`src/dsw_translation_tool/translation_repository_config.py`][translation-repository-config-py]

Test with:

- [`tests/infra/test_translation_repository_config.py`][test-translation-repository-config-py]

### KM Registry Discovery or Guarded KM Updates

Start with:

- [`src/dsw_translation_tool/km_registry.py`][km-registry-py]
- [`src/dsw_translation_tool/km_bundle_sync.py`][km-bundle-sync-py]
- [`src/dsw_translation_tool/km_latest_sync.py`][km-latest-sync-py]

Test with:

- [`tests/infra/test_km_registry.py`][test-km-registry-py]
- [`tests/infra/test_km_bundle_sync.py`][test-km-bundle-sync-py]
- [`tests/infra/test_km_latest_sync.py`][test-km-latest-sync-py]

### GitHub Workflow Wiring

Start with:

- [`examples/github-actions/`][examples-github-actions]

Test with:

- [`tests/infra/test_github_workflows.py`][test-github-workflows-py]

If the right place is unclear, add or adjust a small test that describes the
behavior you expect. The module ownership usually becomes obvious from there.

[ci-sync-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/dsw_translation_tool/ci_sync.py
[examples-github-actions]: https://github.com/ThreeMonth03/DSW_Translation_tool/tree/master/examples/github-actions
[km-bundle-sync-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/dsw_translation_tool/km_bundle_sync.py
[km-latest-sync-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/dsw_translation_tool/km_latest_sync.py
[km-registry-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/dsw_translation_tool/km_registry.py
[knowledge-model-service-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/dsw_translation_tool/knowledge_model_service.py
[localize-merge-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/dsw_translation_tool/localize_merge.py
[localize-sync-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/dsw_translation_tool/localize_sync.py
[repository-ci-sync-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/dsw_translation_tool/repository_ci_sync.py
[shared-blocks-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/dsw_translation_tool/shared_blocks.py
[package-dir]: https://github.com/ThreeMonth03/DSW_Translation_tool/tree/master/src/dsw_translation_tool
[src-root]: https://github.com/ThreeMonth03/DSW_Translation_tool/tree/master/src
[sync-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/dsw_translation_tool/sync.py
[sync-shared-strings-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/sync_shared_strings.py
[test-ci-sync-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/tests/infra/test_ci_sync.py
[test-cli-sync-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/tests/infra/test_cli_sync.py
[test-github-workflows-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/tests/infra/test_github_workflows.py
[test-km-bundle-sync-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/tests/infra/test_km_bundle_sync.py
[test-km-latest-sync-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/tests/infra/test_km_latest_sync.py
[test-km-registry-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/tests/infra/test_km_registry.py
[test-localize-merge-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/tests/infra/test_localize_merge.py
[test-localize-sync-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/tests/infra/test_localize_sync.py
[test-shared-string-sync-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/tests/translation/test_shared_string_sync.py
[test-translation-repository-config-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/tests/infra/test_translation_repository_config.py
[tests-translation]: https://github.com/ThreeMonth03/DSW_Translation_tool/tree/master/tests/translation
[translation-repository-config-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/dsw_translation_tool/translation_repository_config.py
[tree-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/dsw_translation_tool/tree.py
[workflow-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/dsw_translation_tool/workflow.py
