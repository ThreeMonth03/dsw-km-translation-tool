# Translation Repository Bootstrap

Use this page when creating a new dedicated translation repository from the
tooling repository.

## What Bootstrap Does

The bootstrap command turns an empty checkout into a working translation
repository:

- writes `translation-config.yml` from a template;
- copies repository docs and GitHub Actions workflows;
- downloads the configured KM bundle from the DSW Registry;
- downloads the current Localize/Weblate PO;
- expands the PO/KM pair into `tree/`;
- builds `builds/final_translated.po` and `builds/final_translated.km`;
- writes review output under `reviews/`.

It does not commit, push, configure GitHub secrets, or upload translations to
Weblate.

## Command

From the tooling repository:

```shell
export DSW_REGISTRY_TOKEN=...
make repo-init NEW_TRANSLATION_REPO_DIR=/path/to/new-translation-repo
```

By default this uses [`examples/translation-config.yml`][example-config]. For a
custom repository, copy that file, edit the KM/language/Weblate/tooling values,
and pass it explicitly:

```shell
make repo-init \
  NEW_TRANSLATION_REPO_DIR=/path/to/new-translation-repo \
  TRANSLATION_CONFIG_TEMPLATE=/path/to/translation-config.yml
```

Use scaffold-only mode when you want to review config/docs/workflows before any
network downloads:

```shell
.venv/bin/dsw-km-init-translation-repo \
  --repo-root /path/to/new-translation-repo \
  --tooling-repo . \
  --config-template /path/to/translation-config.yml \
  --scaffold-only
```

## After Bootstrap

1. Review generated files.
2. Create the GitHub repository and push the first commit.
3. Configure repository secrets:
   - `LOCALIZE_API_TOKEN`
   - `DSW_REGISTRY_TOKEN`
4. Run `localize_alignment_report.yml`.
5. Run `localize_auto_sync.yml` and confirm it creates no unexpected changes.

## Template Ownership

- Translation repository docs are copied from
  [`examples/translation-repository/`][translation-repo-template].
- GitHub Actions workflows are copied from
  [`examples/github-actions/`][github-actions-templates].
- Workflow `TOOLING_REPOSITORY`, `TOOLING_REF`, and tracking branch values are
  rendered from `translation-config.yml`.

[example-config]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/examples/translation-config.yml
[github-actions-templates]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/examples/github-actions
[translation-repo-template]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/examples/translation-repository
