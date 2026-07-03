# Development Guidelines

These rules keep the tooling maintainable as Weblate sync, KM bundles, and
translation-tree behavior evolve.

## Source and Generated Files

Commit source and durable examples:

- [`src/`][src-dir]
- [`tests/`][tests-dir]
- [`config/`][config-dir]
- [`examples/`][examples-dir]
- [`docs/`][docs-dir]
- small fixture inputs under [`files/`][files-dir]
- durable translation round-trip fixtures under [`tests/fixtures/`][tests-fixtures-dir]

Local generated state stays out of normal tooling commits:

- `.venv/`
- Python caches
- `.pytest_cache/`
- `.ruff_cache/`
- local backup directories
- local `translation/` workspaces

Translation round-trip fixtures keep the checked-in tree, final PO, and review
diff. KM bundles are rebuilt by tests and workflows instead of stored in the
fixture tree.

Dedicated translation repositories may commit generated `tree/`, `builds/`, and
`reviews/` artifacts because those files are the automation and visualization
workspace for translators and maintainers.

## Code Organization

- Keep root [`src/*.py`][src-dir] files as command-line shims.
- Put reusable logic in [`src/dsw_translation_tool/`][package-dir].
- Keep GitHub Actions YAML thin. YAML should describe checkout, setup, and the
  one helper command it runs.
- Add or update tests under [`tests/infra/`][tests-infra-dir] when a helper makes a Git, Weblate,
  config, or merge decision.
- Add or update tests under [`tests/translation/`][tests-translation-dir] when a change affects
  translator-facing tree files or PO/KM output.
- Update docs in the same commit as behavior changes.
- Update Sphinx pages or docstrings when stable package APIs change.

## Localize/Weblate Safety

- Treat the latest Weblate state as authoritative for zh-Hant production sync.
- Keep production automation one-way from Weblate to Git.
- Store Weblate and DSW API tokens in repository secrets.
- Preserve Weblate review-state flags during sync.

## KM Version Policy

The current zh-Hant production policy is latest-only. Add a newer KM after it
is published by the DSW Registry and the translation repository config has been
reviewed.

## Standard Checks

Before pushing tooling changes:

```shell
make check
```

For workflow template or config changes, also validate a real translation
repository config and compare the template with the formal workflow:

```shell
.venv/bin/python src/validate_translation_config.py \
  --config /path/to/translation-repo/translation-config.yml
diff -u examples/github-actions/localize_auto_sync_template.yml \
  /path/to/translation-repo/.github/workflows/localize_auto_sync.yml
```

For Localize/Weblate sync changes, run a dry run against a disposable checkout
or use a test translation repository before updating the formal public repo.

[config-dir]: https://github.com/ThreeMonth03/DSW_Translation_tool/tree/master/config
[docs-dir]: https://github.com/ThreeMonth03/DSW_Translation_tool/tree/master/docs
[examples-dir]: https://github.com/ThreeMonth03/DSW_Translation_tool/tree/master/examples
[files-dir]: https://github.com/ThreeMonth03/DSW_Translation_tool/tree/master/files
[package-dir]: https://github.com/ThreeMonth03/DSW_Translation_tool/tree/master/src/dsw_translation_tool
[src-dir]: https://github.com/ThreeMonth03/DSW_Translation_tool/tree/master/src
[tests-dir]: https://github.com/ThreeMonth03/DSW_Translation_tool/tree/master/tests
[tests-fixtures-dir]: https://github.com/ThreeMonth03/DSW_Translation_tool/tree/master/tests/fixtures
[tests-infra-dir]: https://github.com/ThreeMonth03/DSW_Translation_tool/tree/master/tests/infra
[tests-translation-dir]: https://github.com/ThreeMonth03/DSW_Translation_tool/tree/master/tests/translation
