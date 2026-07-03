# KM Update Runbook

Use this runbook when the DSW Registry publishes a new Common DSW Knowledge
Model. The production translation repository tracks the current published KM.

## When to Start

Start after the KM version is published and available from the DSW Registry or
another official upstream source.

The scheduled KM version auto-update workflow is the normal update mechanism.
It runs [`sync_latest_km.py`][sync-latest-km-py], no-ops when the configured KM
is current, and only pushes to Git when every safety check passes. When the
Registry has a newer published KM, the workflow:

- downloads the new KM bundle using `DSW_REGISTRY_TOKEN`;
- updates `translation-config.yml` and the conventional source KM path;
- downloads the current Weblate PO without uploading anything to Weblate;
- rebuilds `tree/`, `builds/final_translated.po`, and
  `builds/final_translated.km`;
- validates config, runs translation tests, and checks repository alignment;
- commits and pushes to the tracking branch only after those steps pass.

If the token is missing or any validation step fails, no Git commit is pushed.
The next scheduled run will retry.

For a local maintainer run, use:

```shell
make repo-km-update TRANSLATION_REPO_DIR=/path/to/dsw-root-locales-zh_Hant
```

## Dry-Run First

Work in a disposable branch or local clone first.

1. Discover available versions:

   ```shell
   make repo-km-status TRANSLATION_REPO_DIR=/path/to/dsw-root-locales-zh_Hant
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
- newly review-marked translations reported by Weblate.

Merge only after the dry-run branch produces aligned artifacts. After merge,
trigger the scheduled sync and alignment report once manually to verify the
production branch.

[sync-latest-km-py]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/src/sync_latest_km.py
