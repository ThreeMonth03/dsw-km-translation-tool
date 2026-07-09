# Workflow Templates

Use this page when reviewing or manually updating GitHub Actions workflows in a
dedicated translation repository. New repositories should usually be created
with [Translation Repository Bootstrap](translation-repository-bootstrap.md)
instead of copying each file by hand. The templates live in
[`examples/github-actions/`][github-actions-templates].

The tooling repository also has its own
[`upstream_smoke.yml`][upstream-smoke-workflow]. That workflow is not a template
for translation repositories; it checks whether the current upstream Registry KM
and Weblate PO still build with this tool.

The templates assume the translation repository also has a
`translation-config.yml` shaped like
[`examples/translation-config.yml`][example-translation-config]. Keep repository
names, branch names, KM bundle paths, language metadata, and Localize metadata
in that config rather than hard-coding them into workflow steps.

## Which Template to Use

| Template | Installs In | Writes Git? | Secrets | Use |
| --- | --- | --- | --- | --- |
| [`validate_translation_config_template.yml`][validate-template] | Translation repository | No | None | Validate config on pushes, pull requests, or manual runs. |
| [`localize_auto_sync_template.yml`][auto-sync-template] | Translation repository | Yes | None | Pull Weblate into Git, rebuild outputs, and commit changed files. PRs with translation edits get a report instead of writer sync. |
| [`github_translation_import_template.yml`][github-import-template] | Translation repository | Yes | `LOCALIZE_API_TOKEN` | After merge, import accepted GitHub translation edits to Weblate, then sync Weblate back to Git. |
| [`localize_status_report_template.yml`][status-template] | Translation repository | No | Optional `LOCALIZE_API_TOKEN` | Report Weblate PO health and website-side checks. |
| [`localize_alignment_report_template.yml`][alignment-template] | Translation repository | No | None | Verify Weblate, tree, final PO, and final KM outputs still match. |
| [`km_version_auto_update_template.yml`][km-update-template] | Translation repository | Yes | `DSW_REGISTRY_TOKEN` | Move to a newer published KM only after validation passes. |

## Variables to Review

Each workflow template has a small `env` block. Review these values when copying
or updating a workflow:

```yaml
TOOLING_REPOSITORY: ThreeMonth03/dsw-km-translation-tool
TOOLING_REF: master
TRACKING_BRANCH: master
TRANSLATION_CONFIG: translation-config.yml
```

Use `TOOLING_REF: master` while the translation repository should track the
latest automation. Switch to a tag only if the translation repository needs a
frozen tooling version.

## Permissions and Secrets

Read-only workflows should use `contents: read`. Writer workflows need
`contents: write` because they commit generated outputs back to the translation
repository.

Configure secrets in the translation repository, not in this tooling
repository. See [Security and Permissions](security-and-permissions.md) for the
current secret list and placement.

`github_translation_import_template.yml` is the only translation-repository
workflow that writes Weblate. It runs after reviewed changes reach `master`,
imports only safe GitHub translation edits, and fails with a report if Weblate
changed the same entries differently.

`localize_auto_sync_template.yml` compares pull-request translation reports
against the pull request's base commit, not whatever `master` contains when a
runner starts. It also checks that a same-repository pull-request branch still
exists before attempting writer sync. This keeps delayed PR runs from failing
after the PR was already merged and its branch deleted.

## Update Checklist

When a workflow behavior changes:

1. Update the template in [`examples/github-actions/`][github-actions-templates].
2. Update tests that validate workflow wiring, especially
   [`tests/infra/test_github_workflows.py`][test-github-workflows].
3. Copy the reviewed template into each production translation repository that
   uses it.
4. Run the read-only validation, status, and alignment workflows before relying
   on writer workflows.

[alignment-template]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/examples/github-actions/localize_alignment_report_template.yml
[auto-sync-template]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/examples/github-actions/localize_auto_sync_template.yml
[example-translation-config]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/examples/translation-config.yml
[github-import-template]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/examples/github-actions/github_translation_import_template.yml
[github-actions-templates]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/examples/github-actions
[km-update-template]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/examples/github-actions/km_version_auto_update_template.yml
[status-template]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/examples/github-actions/localize_status_report_template.yml
[test-github-workflows]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/tests/infra/test_github_workflows.py
[upstream-smoke-workflow]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/.github/workflows/upstream_smoke.yml
[validate-template]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/examples/github-actions/validate_translation_config_template.yml
