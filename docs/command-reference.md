# Command Reference

Use `make` for normal maintenance. Use the packaged `dsw-km-*` commands only
when you are changing workflow wiring, debugging one helper, or reproducing a
GitHub Actions command exactly.

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
GITHUB_TRANSLATION_BASE_REF=origin/master
GITHUB_TRANSLATION_HEAD_REF=HEAD
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
| `make upstream-smoke` | Check current upstream KM/Weblate inputs in `.cache/upstream-smoke/` |

## Translation Repository

Set `TRANSLATION_REPO_DIR` before running these targets.

| Target | Safety | Use |
| --- | --- | --- |
| `make repo-validate` | Read-only | Validate `translation-config.yml` |
| `make repo-status` | Report files only | Inspect the checked-in Weblate PO |
| `make repo-checks` | Report files only | Query Weblate quality checks such as `has:check` |
| `make repo-align` | Report files only | Compare Weblate, tree, and final PO outputs |
| `make repo-scaffold-check` | Read-only | Verify managed docs and workflows match the tooling templates |
| `make repo-scaffold-sync` | Filesystem writer | Refresh managed docs and workflows without changing config or translations |
| `make repo-sync-shared-strings` | Filesystem writer | Expand canonical shared-block translations into referenced tree fields |
| `make repo-github-translations` | Report files only | Compare GitHub translation edits with current Weblate |
| `make repo-init` | Writes files | Initialize a new translation repository from templates and upstream inputs |
| `make repo-pull-po` | Writes files | Refresh `sources/localize/` in the checkout |
| `make repo-sync` | Git writer | Pull Weblate, rebuild outputs, and commit/push when changed |
| `make repo-import-github-translations` | Weblate writer | Import accepted GitHub translation edits, failing on conflicts |
| `make repo-km-status` | Report files only | Check whether the Registry has a newer KM |
| `make repo-km-update` | Guarded Git writer | Update to a newer published KM after validation passes |

## Native Locale Validation

Validate a generated PO directly before importing it into DSW:

```shell
.venv/bin/dsw-km-validate-locale \
  --po /path/to/translation-repo/builds/final_translated.po \
  --km /path/to/source.km \
  --target-language zh_Hant
```

The command is read-only unless `--report` is supplied. It checks gettext
syntax, the exact PO `Language` header, and every UUID, field, and source string
against the source KM. It validates an existing PO; it does not generate a PO
or create a translated KM package. It does not contact a DSW server.
It cannot detect source messages absent from the PO. Use
[Native Locale Verification](native-locale-verification.md) to compare against
an official POT and test browser import in an isolated DSW instance.

Audit the shared Weblate source catalog using an already exported official POT:

```shell
.venv/bin/dsw-km-report-source-catalog \
  --repo-root /path/to/translation-repo \
  --official-pot /tmp/native-dsw-review/official.pot \
  --out /tmp/upstream-source-review
```

Use a new output directory. The command reads the public upstream repository
configured by `localize.repository` and writes a snapshot and reports only.
It does not upload to Weblate, edit translations or create a pull request.
Source differences produce warnings; invalid inputs and download failures fail.

Plan a native locale release without publishing it (requires an authenticated
GitHub CLI and a checkout containing all tags):

```shell
.venv/bin/dsw-km-plan-locale-release \
  --repo-root /path/to/translation-repo \
  --repository owner/translation-repo
```

The planner compares usable translations with published locale releases and
prints either the next unused revision or a no-change result.

Prepare native locale release assets without publishing them:

```shell
.venv/bin/dsw-km-prepare-locale-release \
  --repo-root /path/to/translation-repo \
  --tooling-repo . \
  --tag locale-zh_Hant-r1 \
  --out /tmp/native-locale-release
```

The command requires clean tracked files, a full `tooling.ref` commit SHA,
the matching tooling checkout, and a reproducible rebuild. The output directory
must not exist. It writes PO assets, checksums, and provenance only; see
[Releases](releases.md) for the publication workflow and tag conventions.

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
`repo-km-pull`, or `repo-sync-branch`.

## Direct CLI Use

The targets above are thin wrappers around console scripts installed into
`.venv/bin/`. Those commands are declared in [`pyproject.toml`][pyproject] and
implemented under [`src/dsw_km_translation_tool/cli/`][cli-dir].

When changing implementation, use [Architecture](architecture.md) to find the
owning package module and tests.

## Local Tree Variables

The local tree targets accept these Make variable overrides from
[`Makefile`][makefile]:

```shell
PO=tests/fixtures/source_inputs/common_dsw_zh_Hant.po
MODEL=tests/fixtures/source_inputs/dsw_root_2.7.0.km
TARGET_LANG=zh_Hant
OUTPUT_ROOT=translation/zh_Hant
```

Production translation repositories should use `translation-config.yml` and the
`repo-*` targets instead.

[example-translation-config]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/examples/translation-config.yml
[cli-dir]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/src/dsw_km_translation_tool/cli
[makefile]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/Makefile
[pyproject]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/pyproject.toml
