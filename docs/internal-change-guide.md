# Internal Change Guide

Use this page when a change goes below the maintainer-facing services listed in
the package reference. Internal modules are not public APIs; they are
implementation areas with focused tests.

Start from the behavior you need to change, then read the owning facade and the
support modules together. Prefer adding or adjusting a small test before editing
the support code.

## Change Map

| Behavior | Start With | Internal Area | Tests |
| --- | --- | --- | --- |
| Translation tree folder names or path layout | [`tree.py`][tree-py] | [`tree_support/naming.py`][tree-naming-py], [`tree_support/storage.py`][tree-storage-py], [`layout.py`][layout-py] | [`tests/translation/`][tests-translation], tree CLI tests under [`tests/infra/`][tests-infra] |
| Translation Markdown parse/render format | [`tree.py`][tree-py] | [`tree_support/document.py`][tree-document-py], [`tree_support/snapshot.py`][tree-snapshot-py] | [`tests/translation/test_tree_roundtrip.py`][test-tree-roundtrip-py], [`tests/translation/test_tree_export.py`][test-tree-export-py] |
| Tree validation or untranslated status reports | [`tree.py`][tree-py], [`workflow.py`][workflow-py] | [`tree_support/reporting.py`][tree-reporting-py] | tree and status CLI tests under [`tests/infra/`][tests-infra] |
| PO parsing, escaping, or rewrite output | [`po.py`][po-py] | [`po_support/parser.py`][po-parser-py], [`po_support/codec.py`][po-codec-py], [`po_support/render.py`][po-render-py], [`po_support/writer.py`][po-writer-py] | PO/KM tests under [`tests/translation/`][tests-translation] |
| KM event merge, tree derivation, validation, or rewrite | [`knowledge_model_service.py`][km-service-py] | [`knowledge_model_support/`][km-support-dir], [`dsw_models_adapter.py`][dsw-models-adapter-py] | [`tests/infra/test_dsw_models_parser.py`][test-dsw-models-py], PO/KM tests under [`tests/translation/`][tests-translation] |
| Shared-string grouping and sync behavior | [`sync.py`][sync-py], [`shared_blocks/`][shared-blocks-dir] | [`sync_support/`][sync-support-dir] | [`tests/translation/test_shared_string_sync.py`][test-shared-sync-py], sync CLI tests under [`tests/infra/`][tests-infra] |
| GitHub translation PR/import policy | [`github_translation_contributions.py`][github-translation-contributions-py], [`weblate_upload.py`][weblate-upload-py] | PO state parsing in [`po_support/state.py`][po-state-py] and the Weblate upload client | [`tests/infra/test_github_translation_contributions.py`][test-github-translations-py], [`tests/infra/test_weblate_upload.py`][test-weblate-upload-py] |
| CI writer commit or recovery behavior | [`ci_sync.py`][ci-sync-py], [`repository_ci_sync.py`][repository-ci-sync-py] | Git command helpers in [`command.py`][command-py] | [`tests/infra/test_ci_sync.py`][test-ci-sync-py] |
| KM Registry discovery or latest-KM update behavior | [`km_registry.py`][km-registry-py], [`km_latest_sync.py`][km-latest-sync-py] | [`km_bundle_sync.py`][km-bundle-sync-py] and helper functions in the same modules | KM tests under [`tests/infra/`][tests-infra] |
| New translation repository scaffold or hydration | [`translation_repository_bootstrap.py`][translation-repository-bootstrap-py] | Templates in [`examples/translation-repository/`][translation-repo-template-dir] and [`examples/github-actions/`][github-actions-templates] | [`tests/infra/test_translation_repository_bootstrap.py`][test-bootstrap-py] |
| GitHub Actions template wiring | [`examples/github-actions/`][github-actions-templates] | Workflow templates and packaged CLI modules in [`src/dsw_km_translation_tool/cli/`][cli-dir] | [`tests/infra/test_github_workflows.py`][test-github-workflows-py] |

## Editing Rules

- Keep packaged CLI behavior under
  [`src/dsw_km_translation_tool/cli/`][cli-dir] and expose user-facing commands
  through [`pyproject.toml`][pyproject].
- Keep GitHub Actions YAML as orchestration; branch selection, GitHub import
  policy, KM rewriting, and commit decisions belong in Python.
- Keep support modules behavior-focused. If an internal helper starts serving
  several unrelated workflows, promote a clearer facade before adding more
  conditions.
- Update the package reference only when a maintainer-facing facade, report
  model, or config contract changes.

[ci-sync-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/ci_sync.py
[cli-dir]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/src/dsw_km_translation_tool/cli
[command-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/command.py
[dsw-models-adapter-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/dsw_models_adapter.py
[github-actions-templates]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/examples/github-actions
[github-translation-contributions-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/github_translation_contributions.py
[km-bundle-sync-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/km_bundle_sync.py
[km-latest-sync-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/km_latest_sync.py
[km-registry-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/km_registry.py
[km-service-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/knowledge_model_service.py
[km-support-dir]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/src/dsw_km_translation_tool/knowledge_model_support
[layout-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/layout.py
[po-state-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/po_support/state.py
[po-codec-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/po_support/codec.py
[po-parser-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/po_support/parser.py
[po-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/po.py
[po-render-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/po_support/render.py
[po-writer-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/po_support/writer.py
[pyproject]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/pyproject.toml
[repository-ci-sync-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/repository_ci_sync.py
[shared-blocks-dir]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/src/dsw_km_translation_tool/shared_blocks
[sync-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/sync.py
[sync-support-dir]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/src/dsw_km_translation_tool/sync_support
[test-ci-sync-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/tests/infra/test_ci_sync.py
[test-dsw-models-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/tests/infra/test_dsw_models_parser.py
[test-github-workflows-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/tests/infra/test_github_workflows.py
[test-github-translations-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/tests/infra/test_github_translation_contributions.py
[test-bootstrap-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/tests/infra/test_translation_repository_bootstrap.py
[test-shared-sync-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/tests/translation/test_shared_string_sync.py
[test-tree-export-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/tests/translation/test_tree_export.py
[test-tree-roundtrip-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/tests/translation/test_tree_roundtrip.py
[test-weblate-upload-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/tests/infra/test_weblate_upload.py
[tests-infra]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/tests/infra
[tests-translation]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/tests/translation
[translation-repo-template-dir]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/examples/translation-repository
[translation-repository-bootstrap-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/translation_repository_bootstrap.py
[tree-document-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/tree_support/document.py
[tree-naming-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/tree_support/naming.py
[tree-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/tree.py
[tree-reporting-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/tree_support/reporting.py
[tree-snapshot-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/tree_support/snapshot.py
[tree-storage-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/tree_support/storage.py
[weblate-upload-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/weblate_upload.py
[workflow-py]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/src/dsw_km_translation_tool/workflow.py
