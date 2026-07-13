# Development Guidelines

These rules keep the tooling maintainable as Weblate sync, KM bundles, and
translation-tree behavior evolve.

## Source and Generated Files

Commit source and durable examples:

- [`src/`][src-dir]
- [`pyproject.toml`][pyproject]
- [`tests/`][tests-dir]
- [`config/`][config-dir]
- [`examples/`][examples-dir]
- [`docs/`][docs-dir]
- offline source inputs under [`tests/fixtures/source_inputs/`][source-inputs-fixture-dir]
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
`reviews/` outputs because those files are the automation and visualization
workspace for translators and maintainers.

## Code Organization

- Put packaged CLI behavior under
  [`src/dsw_km_translation_tool/cli/`][cli-dir] and expose user-facing commands
  through [`pyproject.toml`][pyproject].
- Put reusable logic in [`src/dsw_km_translation_tool/`][package-dir].
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
- Allow Git-to-Weblate writes only through the guarded post-merge translation
  import workflow.
- Store Weblate and DSW API tokens as described in
  [Security and Permissions](security-and-permissions.md).
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

When you need to verify current upstream services and data shape, run:

```shell
make upstream-smoke
```

This requires `DSW_REGISTRY_TOKEN`. It downloads the current Weblate PO and
uses a cacheable workspace under `.cache/upstream-smoke/`; it does not write to
the production translation repository.

For workflow template changes, update the template, run scaffold sync against
the production translation repository, then let normal repository CI validate
both sides. For production sync behavior changes, test against a disposable
translation checkout before touching the production translation repository.

[config-dir]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/config
[cli-dir]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/src/dsw_km_translation_tool/cli
[docs-dir]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/docs
[examples-dir]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/examples
[package-dir]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/src/dsw_km_translation_tool
[pyproject]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/pyproject.toml
[source-inputs-fixture-dir]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/tests/fixtures/source_inputs
[src-dir]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/src
[tests-dir]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/tests
[tests-fixtures-dir]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/tests/fixtures
[tests-infra-dir]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/tests/infra
[tests-translation-dir]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/tests/translation
