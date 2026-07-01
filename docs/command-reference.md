# Command Reference

This page is command-focused. See the architecture and runbook documents for
why each command exists.

Use variables so commands survive repo moves:

```shell
TOOL_REPO_DIR=/path/to/DSW_Translation_tool
TRANSLATION_REPO_DIR=/path/to/dsw-root-locales-zh_Hant
```

## Setup and Checks

```shell
make install-dev
make format
make format-check
make lint
make test
make test-infra
make test-translation
git diff --check
```

## Legacy Local Translation Tree

These commands operate on the tooling repository's local
`translation/zh_Hant/` workspace.

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
MODEL=files/dsw_root_2.7.0.km
TARGET_LANG=zh_Hant
OUTPUT_ROOT=translation/zh_Hant
```

## External Translation Repository Validation

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
  --json-out "$TRANSLATION_REPO_DIR/reviews/localize_status_report.json"
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

## One-Shot Repository-To-Weblate Migration

Prepare a dry-run migration PO:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/migrate_reviewed_to_localize.py" \
  --repo-root "$TRANSLATION_REPO_DIR" \
  --config translation-config.yml \
  --chapters 0004 0005 0006 \
  --fill-localize-blanks-from-repo
```

Apply after reviewing the generated report:

```shell
LOCALIZE_API_TOKEN=... \
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/migrate_reviewed_to_localize.py" \
  --repo-root "$TRANSLATION_REPO_DIR" \
  --config translation-config.yml \
  --chapters 0004 0005 0006 \
  --fill-localize-blanks-from-repo \
  --apply
```

## KM Bundle Helpers

Discover configured or registry-published KM versions:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/discover_km_versions.py" \
  --config "$TRANSLATION_REPO_DIR/translation-config.yml"
```

Pull the latest configured KM bundle when repository policy allows it:

```shell
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/pull_km_bundle.py" \
  --repo-root "$TRANSLATION_REPO_DIR" \
  --config translation-config.yml
```
