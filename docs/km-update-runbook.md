# KM Update Runbook

Use this runbook when the DSW Registry publishes a new Common DSW Knowledge
Model. The production policy is latest-only: the translation repository tracks
the current published KM rather than maintaining parallel version branches.

## When to Start

Start only after the KM version is published and available from the DSW
Registry or another official upstream source. Do not add draft or unpublished
bundles, such as a not-yet-published `2.8.0`.

## Dry-Run First

Work in a disposable branch or local clone first.

1. Discover available versions:

   ```shell
   "$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/discover_km_versions.py" \
     --config "$TRANSLATION_REPO_DIR/translation-config.yml"
   ```

2. Pull the published KM bundle:

   ```shell
   "$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/pull_km_bundle.py" \
     --repo-root "$TRANSLATION_REPO_DIR" \
     --config translation-config.yml
   ```

3. Update `translation-config.yml`:

   - set `knowledge_model.supported_versions` to the new latest version;
   - point `knowledge_model.bundle_path` at the new bundle;
   - keep the tracking branch as `master` unless repository policy changes.

4. Validate config:

   ```shell
   "$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/validate_translation_config.py" \
     --config "$TRANSLATION_REPO_DIR/translation-config.yml"
   ```

5. Run Localize/Weblate sync on the disposable branch:

   ```shell
   "$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/sync_from_localize.py" \
     --host-repo "$TRANSLATION_REPO_DIR" \
     --tooling-repo "$TOOL_REPO_DIR" \
     --config translation-config.yml \
     --translation-root . \
     --target-ref "$BRANCH_NAME" \
     --restore-source-ref origin/master \
     --mode pull_request
   ```

6. Run the alignment report:

   ```shell
   "$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/report_alignment_status.py" \
     --repo-root "$TRANSLATION_REPO_DIR" \
     --config translation-config.yml \
     --artifact-dir "$TRANSLATION_REPO_DIR/reviews/localize_alignment_artifacts" \
     --fail-on-mismatch
   ```

## Review Before Merge

Review these generated files before merging:

```text
sources/knowledge-models/
sources/localize/zh_Hant/latest.po
tree/
builds/final_translated.po
builds/final_translated.km
reviews/
```

Pay special attention to:

- source mismatches, which may indicate changed English strings;
- missing entries, which may indicate new KM fields or removed old fields;
- newly empty translations;
- newly fuzzy or needs-editing translations reported by Weblate.

Merge only after the dry-run branch produces aligned artifacts. After merge,
trigger the scheduled sync and alignment report once manually to verify the
production branch.
