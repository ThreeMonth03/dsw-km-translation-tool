# Workflow Templates

Use this page when reviewing or changing GitHub Actions workflows managed for a
dedicated translation repository. Create new repositories with
[Translation Repository Bootstrap](translation-repository-bootstrap.md), and
refresh existing repositories with scaffold sync. The templates live in
[`examples/github-actions/`][github-actions-templates].

The tooling repository also has its own
[`upstream_smoke.yml`][upstream-smoke-workflow]. That workflow is not a template
for translation repositories; it checks whether the current upstream Registry KM
and Weblate PO still build with this tool.

The templates assume the translation repository also has a
`translation-config.yml` shaped like
[`examples/translation-config.yml`][example-translation-config]. Keep repository
names, branch names, KM coordinates, language metadata, and Localize metadata
in that config rather than hard-coding them into workflow steps.

## Which Template to Use

| Template | Installs In | Writes Git? | Secrets | Use |
| --- | --- | --- | --- | --- |
| [`validate_translation_config_template.yml`][validate-template] | Translation repository | No | None | Validate config and scaffold state; report translation changes on pull requests. |
| [`localize_auto_sync_template.yml`][auto-sync-template] | Translation repository | Yes | None | Pull Weblate into Git and rebuild outputs on trusted scheduled runs. |
| [`github_translation_import_template.yml`][github-import-template] | Translation repository | Yes | `LOCALIZE_API_TOKEN` | After merge, import accepted GitHub translation edits to Weblate, then sync Weblate back to Git. |
| [`localize_status_report_template.yml`][status-template] | Translation repository | No | Optional `LOCALIZE_API_TOKEN` | Report Weblate PO health and website-side checks. |
| [`localize_alignment_report_template.yml`][alignment-template] | Translation repository | No | None | Verify Weblate, tree, and final PO outputs still match. |
| [`km_version_auto_update_template.yml`][km-update-template] | Translation repository | Yes | `DSW_REGISTRY_TOKEN` | Move to a newer published KM only after validation passes. |

## Rendered Values

Workflow templates use explicit placeholders such as:

```yaml
TOOLING_REPOSITORY: {{TOOLING_REPOSITORY}}
TOOLING_REF: {{TOOLING_REF}}
TRACKING_BRANCH: {{TRACKING_BRANCH}}
TRANSLATION_CONFIG: translation-config.yml
```

Do not replace them manually. `repo-init` renders them for new repositories;
`repo-scaffold-sync` renders them for existing repositories from
`translation-config.yml`. Unknown placeholders fail instead of leaking into a
workflow.

## Permissions and Secrets

Read-only workflows should use `contents: read`. Writer workflows need
`contents: write` because they commit generated outputs back to the translation
repository.

Configure secrets in the translation repository, not in this tooling
repository. See [Security and Permissions](security-and-permissions.md) for the
current secret list and placement.

`github_translation_import_template.yml` is the only translation-repository
workflow that writes Weblate. It runs after reviewed changes reach `master`,
imports safe new translations and corrections, and fails with a report if Weblate
changed the same entries differently or the translation lost source Markdown
formatting, including boundary whitespace. It resolves canonical shared edits,
rejects competing field edits, and verifies that Weblate applied every uploaded
entry. Detected translation edits trigger a final sync even if Weblate already
contains the proposed text.

`validate_translation_config_template.yml` compares pull-request translation
changes against the base commit recorded by the pull-request event. It checks
Markdown and boundary-whitespace formatting, Weblate conflicts, and shared
translation consistency, then uploads a field-level report. These quality checks
apply to new translations and corrections alike; existing nonempty text is not
frozen. Reviewers keep corrections focused on reported issues. The workflow has
read-only repository permission, receives no secrets, and never modifies the
pull-request branch. It builds and uploads a native PO preview in its temporary
checkout, without requiring translators to commit generated output changes.
It then runs the pinned tooling's native-locale action in disposable official
DSW containers. The same check runs daily, on manual runs, and before locale
releases. Coverage warnings and real screenshots are available in
`native-dsw-review`; import, questionnaire and page-load errors fail the workflow.
Resource-page source fallback is reported separately as a warning. See
[Native Locale Verification](native-locale-verification.md).

Translation operations also enable `audit-source-catalog` on the native-locale
action. It compares the exported POT with the configured public upstream POT,
retaining a source report and immutable snapshot in the same artifact. Source
differences warn; fetch or validation failures fail the audit. Locale releases
leave this live-source audit disabled and verify only their pinned inputs.

`examples/github-actions/release_template.yml` publishes changed native PO locales
after successful sync/import workflows. It validates a clean tracking-branch
checkout against the pinned tooling and
source before publishing native PO assets, checksums, and provenance. See
[Releases](releases.md) for locale revision tags and tooling releases.

`localize_auto_sync_template.yml` is a schedule-only writer. It never executes
for pull requests or processes pull-request-controlled content with write
permission.

All templates that write the tracking branch or Weblate share a
`translation-state-*` concurrency group with `cancel-in-progress: false`.
Keep both settings aligned when adding another writer workflow.

## Update Checklist

When a workflow behavior changes:

1. Update the template in [`examples/github-actions/`][github-actions-templates].
2. Update tests that validate workflow wiring, especially
   [`tests/infra/test_github_workflows.py`][test-github-workflows].
3. Run `make repo-scaffold-sync TRANSLATION_REPO_DIR=/path/to/repo` for each
   production translation repository that uses it.
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
