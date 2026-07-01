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

Do not commit local generated state unless the repository intentionally tracks
it:

- `.venv/`
- Python caches
- `.pytest_cache/`
- `.ruff_cache/`
- local backup directories

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
- Do not add scheduled Git-to-Weblate uploads.
- Use `migrate_reviewed_to_localize.py` only for explicit migration or repair.
- Keep upload commands dry-run by default.
- Never commit Weblate or DSW API tokens. Workflows should read tokens from
  repository secrets.
- Preserve `fuzzy` and `needs editing` semantics. Do not silently approve or
  overwrite strings that are outside the requested migration scope.

## KM Version Policy

The current zh-Hant production policy is latest-only. Do not build automation
around unpublished KM versions. Add a newer KM only after it is published by the
DSW Registry and the translation repository config has been reviewed.

## Standard Checks

Before pushing tooling changes:

```shell
make format-check
make lint
make test
git diff --check
```

For workflow template or config changes, also validate a real translation
repository config:

```shell
.venv/bin/python src/validate_translation_config.py \
  --config /path/to/translation-repo/translation-config.yml
```

For Localize/Weblate sync changes, run a dry run against a disposable checkout
or use a test translation repository before updating the formal public repo.
