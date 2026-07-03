# Architecture

This document maps the repository to the maintenance problems it solves. Use it
when deciding where a change belongs.

## Top-Level Shape

- `readme.md` is the translator-facing entry point and local workflow guide.
- `Makefile` wraps local development checks and the in-repository
  translation-tree workflow.
- `src/*.py` contains command-line entry points used by Make targets and
  GitHub Actions. Keep these files thin.
- `src/dsw_translation_tool/` contains reusable package code.
- `examples/` contains copy-ready workflow templates and an example
  translation repository config.
- `files/` contains small default source PO/KM inputs for local use and tests.
- `docs/sphinx/` contains Sphinx source for developer API documentation.
- `tests/fixtures/translation_tree/` contains the checked-in tree, final PO, and
  review diff used by translation round-trip tests.
- `tests/infra/` covers tooling, CLI, config, and automation behavior.
- `tests/translation/` covers translation-tree and PO/KM round trips.

External production translation repositories usually contain:

```text
translation-config.yml
sources/localize/
sources/knowledge-models/
tree/
builds/
reviews/
```

The tooling repo should be able to run against that layout without keeping
production translation state in the repository root.

## PO, KM, and Tree Layer

These modules handle the local representation of translation data:

- `po.py`: reads and writes PO entries.
- `dsw_models_adapter.py`: adapts DSW KM JSON events into a structure the tools
  can inspect.
- `tree.py`, `outline.py`, `workflow.py`: export and inspect the
  translator-facing folder tree.
- `shared_blocks.py`, `sync.py`, `review.py`: synchronize repeated strings,
  rebuild generated PO files, and produce review diffs.
- `knowledge_model_service.py`: applies translated PO content back into a KM
  bundle.

Keep translator-facing Markdown stable. If a parser change affects field order,
folder names, or shared-block behavior, add focused tests before updating
fixtures.

## Localize/Weblate Sync Layer

These modules connect the translation repository to the Weblate website:

- `translation_repository_config.py`: loads `translation-config.yml` and
  computes repository paths.
- `localize_sync.py`: downloads the current Weblate PO snapshot and can expose
  the previous checked-in snapshot as a temporary comparison file for sync.
- `localize_status.py`: reports PO completion, empty strings, and Weblate
  review-state counts without modifying translations.
- `weblate_checks.py`: reports Weblate units matching quality-check queries
  such as `has:check` without changing translations.
- `alignment_status.py`: verifies that Weblate, the checked-in Localize PO,
  the translation tree, the final PO, and the final KM are mutually aligned.
- `localize_tree_sync.py`: force-refreshes `tree/` from the latest Weblate PO.
- `localize_merge.py`: contains PO merge decisions.
- `ci_sync.py`, `repository_ci_sync.py`: rebuild the translation tree, final PO,
  and final KM, then make Git sync commits.
- `km_bundle_sync.py`, `km_latest_sync.py`, `km_registry.py`: support KM bundle
  discovery and update operations.
- `command.py`: shared subprocess and Git identity helpers used by automation
  writers.

Production zh-Hant sync is Localize/Weblate-first. The normal automation path
is:

```text
Localize/Weblate PO -> tree/ -> builds/final_translated.po -> builds/final_translated.km -> Git commit
```

## GitHub Actions Layer

- `.github/workflows/unittest.yml` validates this tooling repository.
- `examples/github-actions/localize_auto_sync_template.yml` is the
  copy-ready workflow for dedicated translation repositories.
- `examples/github-actions/localize_status_report_template.yml` is the
  read-only status workflow for scheduled Localize/Weblate health reports.
- `examples/github-actions/localize_alignment_report_template.yml` is the
  read-only artifact alignment workflow.
- `examples/github-actions/km_version_auto_update_template.yml` is the guarded
  KM Registry writer. It no-ops when the configured KM is current, and only
  pushes a newer published KM after the bundle pull, Weblate mirror, rebuild,
  config validation, translation tests, and alignment check all pass.
- `examples/github-actions/validate_translation_config_template.yml` is the
  read-only config validation workflow for dedicated translation repositories.

Keep GitHub Actions as orchestration. Branch selection, recovery, PO merge, KM
generation, and commit decisions belong in Python helpers.

## Ownership Rules

- If a change affects Localize/Weblate download or conflict policy, it
  belongs in the Localize sync layer and must be reflected in the runbook.
- If a change affects tree format, shared strings, generated PO, or KM output,
  it belongs in the PO/KM/tree layer and needs round-trip tests.
- If a translation repository needs a new workflow behavior, add it to the
  external template first, then copy the reviewed template into the target repo.
- After changing a workflow template, compare it with the corresponding
  workflow in the formal translation repository.
- If a command changes, update [Command Reference](command-reference.md).
