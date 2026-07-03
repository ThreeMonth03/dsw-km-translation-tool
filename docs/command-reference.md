# Command Reference

Use `make` for normal maintenance. Use the Python scripts directly only when
you are changing workflow wiring, debugging one helper, or reproducing a GitHub
Actions command exactly.

## Required Variables

These are Make variables declared in the repository [`Makefile`][makefile].
Commands that operate on a production-style translation repository need:

```shell
TRANSLATION_REPO_DIR=/path/to/dsw-root-locales-zh_Hant
```

Optional overrides:

```shell
TRANSLATION_CONFIG=translation-config.yml
TRACKING_BRANCH=master
```

Workflow secrets are configured in the production translation repository. Local
commands read `LOCALIZE_API_TOKEN` and `DSW_REGISTRY_TOKEN` from the shell
environment when a target needs them. See
[Security and Permissions](security-and-permissions.md).

Translation repository behavior is configured in `translation-config.yml`; see
[`examples/translation-config.yml`][example-translation-config] for the expected
shape.

## Local Tooling

| Target | Use |
| --- | --- |
| `make install-dev` | Create `.venv` and install development dependencies |
| `make check` | Run format check, lint, compile, tests, docs, and `git diff --check` |
| `make docs` | Build the Sphinx docs into `docs/sphinx/_build/html/` |
| `make format` | Auto-fix Python formatting and import ordering |
| `make help` | Show the common maintainer targets |
| `make help-all` | Show every target, including lower-level local tree helpers |

## Translation Repository

Set `TRANSLATION_REPO_DIR` before running these targets.

| Target | Safety | Use |
| --- | --- | --- |
| `make repo-validate` | Read-only | Validate `translation-config.yml` |
| `make repo-status` | Report files only | Inspect the checked-in Weblate PO |
| `make repo-checks` | Report files only | Query Weblate quality checks such as `has:check` |
| `make repo-align` | Report files only | Compare Weblate, tree, final PO, and final KM artifacts |
| `make repo-pull-po` | Writes files | Refresh `sources/localize/` in the checkout |
| `make repo-sync` | Git writer | Pull Weblate, rebuild artifacts, and commit/push when changed |
| `make repo-km-status` | Report files only | Check whether the Registry has a newer KM |
| `make repo-km-update` | Guarded Git writer | Update to a newer published KM after validation passes |

Example:

```shell
make repo-align TRANSLATION_REPO_DIR=/path/to/dsw-root-locales-zh_Hant
```

## Local Translation Tree

These targets are for development, inspection, and repair in an ignored local
workspace. They default to `translation/zh_Hant/`.

| Target | Use |
| --- | --- |
| `make export-tree` | Export the sample PO/KM into a local translation tree |
| `make sync` | Sync shared strings and rebuild the local final PO |
| `make status` | Show untranslated fields in the local tree |
| `make workflow` | Run the optional end-to-end smoke workflow |

Run `make help-all` if you need lower-level helpers such as `tree-to-po`,
`po-to-km`, `repo-km-pull`, or `repo-sync-branch`.

## Script Map

The targets above are thin wrappers around these scripts. Workflows call the
scripts directly so they can pass explicit paths and GitHub Actions outputs.

| Script | Main Use |
| --- | --- |
| [`validate_translation_config.py`][validate-translation-config-py] | Validate translation repository config |
| [`report_localize_status.py`][report-localize-status-py] | Inspect a checked-out Weblate PO |
| [`report_weblate_checks.py`][report-weblate-checks-py] | Query Weblate quality checks |
| [`report_alignment_status.py`][report-alignment-status-py] | Compare Weblate, tree, PO, and KM artifacts |
| [`pull_localize_po.py`][pull-localize-po-py] | Refresh `sources/localize/` |
| [`sync_from_localize.py`][sync-from-localize-py] | Run the Weblate-to-Git writer |
| [`discover_km_versions.py`][discover-km-versions-py] | Discover Registry KM versions |
| [`sync_latest_km.py`][sync-latest-km-py] | Run the guarded latest-KM writer |
| [`pull_km_bundle.py`][pull-km-bundle-py] | Refresh `sources/knowledge-models/` manually |

## Local Tree Variables

The local tree targets accept these Make variable overrides from
[`Makefile`][makefile]:

```shell
PO=files/knowledge-models-common-dsw-knowledge-model-zh_Hant.po
MODEL=files/<source-km>.km
TARGET_LANG=zh_Hant
OUTPUT_ROOT=translation/zh_Hant
```

Production translation repositories should use `translation-config.yml` and the
`repo-*` targets instead.

[discover-km-versions-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/discover_km_versions.py
[example-translation-config]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/examples/translation-config.yml
[makefile]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/Makefile
[pull-km-bundle-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/pull_km_bundle.py
[pull-localize-po-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/pull_localize_po.py
[report-alignment-status-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/report_alignment_status.py
[report-localize-status-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/report_localize_status.py
[report-weblate-checks-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/report_weblate_checks.py
[sync-from-localize-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/sync_from_localize.py
[sync-latest-km-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/sync_latest_km.py
[validate-translation-config-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/validate_translation_config.py
