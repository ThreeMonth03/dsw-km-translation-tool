# Command Reference

This page is command-focused. See the architecture and runbook documents for
why each command exists.

Use variables so commands survive repo moves:

```shell
TOOL_REPO_DIR=/path/to/DSW_Translation_tool
TRANSLATION_REPO_DIR=/path/to/dsw-root-locales-zh_Hant
```

## Command Safety

Prefer the read-only commands while learning the repository. Writer commands
are intended for reviewed local runs or GitHub Actions workflows.

| Command | Safety | Main Use |
| --- | --- | --- |
| [`validate_translation_config.py`][validate-translation-config-py] | Read-only | Validate `translation-config.yml` |
| [`report_localize_status.py`][report-localize-status-py] | Read-only | Inspect a checked-out Weblate PO |
| [`report_weblate_checks.py`][report-weblate-checks-py] | Read-only | Query Weblate quality checks |
| [`report_alignment_status.py`][report-alignment-status-py] | Read-only | Compare Weblate, tree, PO, and KM artifacts |
| [`discover_km_versions.py`][discover-km-versions-py] without `--fail-on-new-version` | Read-only | Inspect Registry/configured KM versions |
| [`pull_localize_po.py`][pull-localize-po-py] | Writes files | Refresh `sources/localize/` in the checkout |
| [`pull_km_bundle.py`][pull-km-bundle-py] | Writes files | Refresh `sources/knowledge-models/` in the checkout |
| [`sync_from_localize.py`][sync-from-localize-py] | Git writer | Rebuild artifacts and commit/push when changed |
| [`sync_latest_km.py`][sync-latest-km-py] | Guarded Git writer | Update to a newer published KM after validation |

## Setup and Checks

```shell
make install-dev
make format
make format-check
make lint
make test
make test-infra
make test-translation
make docs
git diff --check
```

`make docs` builds the Sphinx developer API reference into
`docs/sphinx/_build/html/`.

## Local Translation Tree

These commands operate on an ignored local workspace. The default path is
`translation/zh_Hant/`.

```shell
make export-tree
make export-tree-force
make status
make sync
make sync-watch
make tree-to-po
make po-to-km
make review-po
make validate
make workflow
```

Important variables:

```shell
PO=files/knowledge-models-common-dsw-knowledge-model-zh_Hant.po
MODEL=files/<source-km>.km
TARGET_LANG=zh_Hant
OUTPUT_ROOT=translation/zh_Hant
```

For production translation repositories, prefer `translation-config.yml` and
the external-repository commands below instead of hard-coding a local `MODEL`
path.

Translation round-trip tests use the checked-in fixture under
[`tests/fixtures/translation_tree/zh_Hant/`][translation-fixture-dir]. Override
`DSW_TRANSLATION_OUTPUT_ROOT` when you intentionally want to test another
workspace.

## External Translation Repository Commands

Validate a dedicated translation repository config:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/validate_translation_config.py" \
  --config "$TRANSLATION_REPO_DIR/translation-config.yml"
```

Pull the current Weblate PO:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/pull_localize_po.py" \
  --repo-root "$TRANSLATION_REPO_DIR" \
  --config translation-config.yml
```

Generate a read-only Localize/Weblate PO status report:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/report_localize_status.py" \
  --po "$TRANSLATION_REPO_DIR/sources/localize/zh_Hant/latest.po" \
  --json-out "$TRANSLATION_REPO_DIR/reviews/localize_status_report.json" \
  --details-out "$TRANSLATION_REPO_DIR/reviews/localize_status_report.md"
```

Generate a read-only Weblate quality-check report:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/report_weblate_checks.py" \
  --repo-root "$TRANSLATION_REPO_DIR" \
  --config translation-config.yml \
  --query has:check \
  --json-out "$TRANSLATION_REPO_DIR/reviews/weblate_checks_report.json" \
  --details-out "$TRANSLATION_REPO_DIR/reviews/weblate_checks_report.md" \
  --allow-api-failure
```

Generate a read-only end-to-end alignment report:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/report_alignment_status.py" \
  --repo-root "$TRANSLATION_REPO_DIR" \
  --config translation-config.yml \
  --json-out "$TRANSLATION_REPO_DIR/reviews/localize_alignment_report.json" \
  --details-out "$TRANSLATION_REPO_DIR/reviews/localize_alignment_report.md" \
  --artifact-dir "$TRANSLATION_REPO_DIR/reviews/localize_alignment_artifacts" \
  --fail-on-mismatch
```

Run the full Localize/Weblate-to-Git writer:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/sync_from_localize.py" \
  --host-repo "$TRANSLATION_REPO_DIR" \
  --tooling-repo "$TOOL_REPO_DIR" \
  --config translation-config.yml \
  --translation-root . \
  --target-ref master \
  --mode schedule
```

For pull request mode:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/sync_from_localize.py" \
  --host-repo "$TRANSLATION_REPO_DIR" \
  --tooling-repo "$TOOL_REPO_DIR" \
  --config translation-config.yml \
  --translation-root . \
  --target-ref feature-branch \
  --restore-source-ref origin/master \
  --mode pull_request
```

## KM Bundle Helpers

Discover configured or registry-published KM versions:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/discover_km_versions.py" \
  --config "$TRANSLATION_REPO_DIR/translation-config.yml"
```

Generate a read-only KM version discovery report:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/discover_km_versions.py" \
  --repo-root "$TRANSLATION_REPO_DIR" \
  --config translation-config.yml \
  --report "$TRANSLATION_REPO_DIR/reviews/km_version_discovery.json" \
  --details-out "$TRANSLATION_REPO_DIR/reviews/km_version_discovery.md" \
  --summary "$TRANSLATION_REPO_DIR/reviews/km_version_discovery_summary.md" \
  --fail-on-new-version
```

Run the guarded latest-KM auto-update writer. It commits and pushes only when
the Registry has a newer published KM and all validation steps pass:

```shell
DSW_REGISTRY_TOKEN=... \
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/sync_latest_km.py" \
  --repo-root "$TRANSLATION_REPO_DIR" \
  --tooling-repo "$TOOL_REPO_DIR" \
  --config translation-config.yml \
  --target-ref master \
  --report "$TRANSLATION_REPO_DIR/reviews/km_auto_update_report.json" \
  --details-out "$TRANSLATION_REPO_DIR/reviews/km_auto_update_report.md" \
  --summary "$TRANSLATION_REPO_DIR/reviews/km_auto_update_summary.md"
```

Pull the latest configured KM bundle when repository policy allows it:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/pull_km_bundle.py" \
  --repo-root "$TRANSLATION_REPO_DIR" \
  --config translation-config.yml
```

[discover-km-versions-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/discover_km_versions.py
[pull-km-bundle-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/pull_km_bundle.py
[pull-localize-po-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/pull_localize_po.py
[report-alignment-status-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/report_alignment_status.py
[report-localize-status-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/report_localize_status.py
[report-weblate-checks-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/report_weblate_checks.py
[sync-from-localize-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/sync_from_localize.py
[sync-latest-km-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/sync_latest_km.py
[translation-fixture-dir]: https://github.com/ThreeMonth03/DSW_Translation_tool/tree/master/tests/fixtures/translation_tree/zh_Hant
[validate-translation-config-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/validate_translation_config.py
