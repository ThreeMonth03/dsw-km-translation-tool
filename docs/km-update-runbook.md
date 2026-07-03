# KM Update Runbook

Use this runbook when the DSW Registry publishes a new Common DSW Knowledge
Model. The production translation repository tracks the current published KM.

## When to Start

Start after the KM version is published and available from the DSW Registry or
another official upstream source.

## Required Secret

Configure `DSW_REGISTRY_TOKEN` in the production translation repository under
GitHub Actions repository secrets before enabling the scheduled KM update
workflow. Local runs read the same token from the shell environment. See
[Security and Permissions](security-and-permissions.md).

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

Set `TRANSLATION_REPO_DIR`, `TARGET_BRANCH`, and related Make variables as
described in the [Command Reference](command-reference.md). The targets are
declared in the [`Makefile`][makefile].

## Dry-Run First

Work in a disposable branch or local clone first.

1. Discover available versions:

   ```shell
   make repo-km-status TRANSLATION_REPO_DIR=/path/to/dsw-root-locales-zh_Hant
   ```

2. Pull the published KM bundle:

   ```shell
   make repo-km-pull TRANSLATION_REPO_DIR="$TRANSLATION_REPO_DIR"
   ```

3. Update `translation-config.yml`:

   - set `knowledge_model.supported_versions` to the new latest version;
   - point `knowledge_model.bundle_path` at the new bundle;
   - keep the tracking branch as `master` unless repository policy changes.

4. Validate config:

   ```shell
   make repo-validate TRANSLATION_REPO_DIR="$TRANSLATION_REPO_DIR"
   ```

5. Run Localize/Weblate sync on the disposable branch:

   ```shell
   make repo-sync-branch \
     TRANSLATION_REPO_DIR="$TRANSLATION_REPO_DIR" \
     TARGET_BRANCH="$BRANCH_NAME"
   ```

6. Run the alignment report:

   ```shell
   make repo-align TRANSLATION_REPO_DIR="$TRANSLATION_REPO_DIR"
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
[makefile]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/Makefile
