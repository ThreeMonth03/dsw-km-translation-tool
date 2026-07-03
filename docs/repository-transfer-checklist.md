# Repository Transfer Checklist

Use this checklist when moving the tooling repository to another GitHub owner or
organization. The goal is to keep translation automation working without
changing translation text or uploading anything to Weblate.

## Before Transfer

1. Confirm the current default branch is green in GitHub Actions.
2. Confirm the formal translation repository is aligned with Weblate:

   ```shell
   "$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/report_alignment_status.py" \
     --repo-root "$TRANSLATION_REPO_DIR" \
     --config translation-config.yml \
     --fail-on-mismatch
   ```

3. Record the target tooling repository owner/name and branch policy.

## Update Tooling References

After the tooling repository is transferred, update every translation repository
that checks out the tooling:

- `translation-config.yml`
  - `tooling.repository`
  - `tooling.ref`, if the branch or tag policy changed
- `.github/workflows/*.yml`
  - `TOOLING_REPOSITORY`
  - `TOOLING_REF`, if the branch or tag policy changed

In this tooling repository, update:

- [`examples/translation-config.yml`][example-translation-config]
- [`examples/github-actions/*_template.yml`][github-actions-templates]
- [`tests/infra/test_github_workflows.py`][test-github-workflows]
- Source links in maintainer docs, starting with
  [`docs/first-time-maintainer.md`][first-time-maintainer], if GitHub redirects
  will not cover the new location.

## GitHub Settings

Verify these settings after transfer:

- Actions are enabled for the tooling repository.
- GitHub Pages is enabled with the `Deploy Documentation` workflow.
- The repository homepage points to the active docs site.
- Required repository secrets are present in each production translation
  repository that needs them.

Secrets are repository settings, not files. Verify them in GitHub after the
move rather than documenting token values.

## Smoke Test

Run these checks after updating references:

```shell
make install-dev
make test
make docs
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/validate_translation_config.py" \
  --config "$TRANSLATION_REPO_DIR/translation-config.yml"
"$TOOL_REPO_DIR/.venv/bin/python" "$TOOL_REPO_DIR/src/report_alignment_status.py" \
  --repo-root "$TRANSLATION_REPO_DIR" \
  --config translation-config.yml \
  --fail-on-mismatch
```

Then trigger the read-only status and alignment workflows manually in the formal
translation repository. Trigger writer workflows only after read-only checks are
green.

[example-translation-config]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/examples/translation-config.yml
[first-time-maintainer]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/docs/first-time-maintainer.md
[github-actions-templates]: https://github.com/ThreeMonth03/DSW_Translation_tool/tree/master/examples/github-actions
[test-github-workflows]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/tests/infra/test_github_workflows.py
