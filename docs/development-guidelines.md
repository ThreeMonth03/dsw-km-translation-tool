# Development Guidelines

These rules keep the tooling maintainable as Weblate sync, KM bundles, and
translation-tree behavior evolve.

## Source and Generated Files

Commit source and durable examples:

- `src/`
- `tests/`
- `config/`
- `examples/`
- `docs/`
- small fixture inputs under `files/`
- durable translation round-trip fixtures under `tests/fixtures/`

Local generated state stays out of normal tooling commits:

- `.venv/`
- Python caches
- `.pytest_cache/`
- `.ruff_cache/`
- local backup directories
- local `translation/` workspaces

Dedicated translation repositories may commit generated `tree/`, `builds/`, and
`reviews/` artifacts because those files are the automation and visualization
workspace for translators and maintainers.

## Code Organization

- Keep root `src/*.py` files as command-line shims.
- Put reusable logic in `src/dsw_translation_tool/`.
- Keep GitHub Actions YAML thin. YAML should describe checkout, setup, and the
  one helper command it runs.
- Add or update tests under `tests/infra/` when a helper makes a Git, Weblate,
  config, or merge decision.
- Add or update tests under `tests/translation/` when a change affects
  translator-facing tree files or PO/KM output.
- Update docs in the same commit as behavior changes.

## Localize/Weblate Safety

- Treat the latest Weblate state as authoritative for zh-Hant production sync.
- Keep production automation one-way from Weblate to Git.
- Store Weblate and DSW API tokens in repository secrets.
- Preserve `fuzzy` and `needs editing` semantics during sync.

## KM Version Policy

The current zh-Hant production policy is latest-only. Add a newer KM after it
is published by the DSW Registry and the translation repository config has been
reviewed.

## Standard Checks

Before pushing tooling changes:

```shell
make format-check
make lint
make test
git diff --check
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
