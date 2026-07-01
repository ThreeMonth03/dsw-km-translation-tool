# Architecture

This document maps the repository to the maintenance problems it solves. Use it
when deciding where a change belongs.

## Top-Level Shape

- `readme.md` is the translator-facing entry point and legacy local workflow
  guide.
- `Makefile` wraps local development checks and the legacy in-repository
  translation-tree workflow.
- `src/*.py` contains command-line entry points used by Make targets and
  GitHub Actions. Keep these files thin.
- `src/dsw_translation_tool/` contains reusable package code.
- `examples/` contains copy-ready workflow and config templates for dedicated
  translation repositories.
- `files/` contains small default source PO/KM inputs for local use and tests.
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

The tooling repo should be able to run against that layout without copying
production data into this repository.

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
- `localize_sync.py`: downloads the current Weblate PO snapshot.
- `localize_tree_sync.py`: force-refreshes `tree/` from the latest Weblate PO.
- `localize_merge.py`: contains PO merge decisions.
- `localize_migration.py`: prepares one-shot repository-to-Weblate migration
  uploads.
- `ci_sync.py`, `versioned_ci_sync.py`: rebuild generated artifacts and make
  Git sync commits.
- `km_bundle_sync.py`, `km_latest_sync.py`, `km_registry.py`: support KM bundle
  discovery and update operations.

Production zh-Hant sync is Localize/Weblate-first. The normal automation path
is:

```text
Localize/Weblate PO -> tree/ -> builds/final_translated.po -> builds/final_translated.km -> Git commit
```

The reverse direction is intentionally manual.

## GitHub Actions Layer

- `.github/workflows/unittest.yml` validates this tooling repository.
- `.github/workflows/translation_auto_sync.yml` is the legacy in-repository
  writer for `translation/zh_Hant`.
- `examples/github-actions/translation_external_auto_sync_template.yml` is the
  copy-ready workflow for dedicated translation repositories.
- `examples/github-actions/localize_reviewed_migration_template.yml` is the
  manual repository-to-Weblate migration workflow.

Keep GitHub Actions as orchestration. Branch selection, recovery, PO merge, KM
generation, and commit decisions belong in Python helpers.

## Ownership Rules

- If a change affects Localize/Weblate download, upload, or conflict policy, it
  belongs in the Localize sync layer and must be reflected in the runbook.
- If a change affects tree format, shared strings, generated PO, or KM output,
  it belongs in the PO/KM/tree layer and needs round-trip tests.
- If a translation repository needs a new workflow behavior, add it to the
  external template first, then copy the reviewed template into the target repo.
- If a command changes, update [Command Reference](command-reference.md).
