## Usage

### For Translators

This section is for people who only need to translate content.
You do not need to understand the Python code in this repository.

For zh-Hant production work, the latest translation state is governed by
Localize/Weblate. The translation tree below is an automation and visualization
workspace for legacy local edits, emergency repairs, generated artifacts, or
one-shot migration work requested by maintainers.

#### 1. Install The Tooling Once

When using this repository for the first time, run:

```shell
make install-dev
```

This creates `.venv` if needed and installs the required Python packages into it.

#### 2. Refresh The Translation Tree From Latest Files (Optional)

Most translators can skip this step, because the collaboration tree is usually
prepared in advance.

If you need to rebuild the tree structure from the latest source files, first
make sure the latest PO and KM files are placed under `files/`.

- The PO file can be downloaded from:
  `https://localize.ds-wizard.org/projects/knowledge-models/common-dsw-knowledge-model/zh_Hant/`
- The KM file can be exported from your local DSW instance.

Then run:

```shell
make export-tree-force
```

This rebuilds the collaboration tree under `translation/zh_Hant/tree` from the
contents of `files/` and discards current tree content after confirmation.

This step prepares the tree and refreshes:

- `translation/zh_Hant/tree/outline.md`
- `translation/zh_Hant/tree/shared_blocks/`

It does not refresh the generated PO or diff outputs. Those are refreshed later
by `make sync`, `make tree-to-po`, or `make review-po`.

#### 3. Open The Translation Tree

After the tree has been prepared, go to `translation/zh_Hant/tree`.

- Each folder represents one node in the knowledge model.
- Each folder contains `_uuid.txt`.
- If the node has translatable content, it also contains `translation.md`.
- Local tree backups are stored separately under `translation/zh_Hant/backups/tree`.
- Backup files are machine-managed local safety copies and are not part of code review.

#### 4. Start `make sync` Or `make sync-watch`

Before you start translating heavily in a fresh clone, run one of these:

```shell
make sync
```

or:

```shell
make sync-watch
```

This seeds the local backup store under `translation/zh_Hant/backups/tree`,
refreshes `translation/zh_Hant/builds/final_translated.po`, and also refreshes
`translation/zh_Hant/reviews/final_translated.diff` and
`translation/zh_Hant/tree/outline.md`, plus
`translation/zh_Hant/tree/shared_blocks/`, and
`translation/zh_Hant/tree/shared_blocks_outline.md`.

It also updates other nodes that share the same original PO translation block.

If a fence is broken or text is typed outside the fenced translation blocks,
the command stops, reports the broken file, and restores that file from its
last known-good backup.

If a translator accidentally deletes `translation.md`, `_uuid.txt`, or even a
whole node folder, the tool attempts to restore it automatically from the tree
manifest and the backup store before continuing.

If you use `make sync-watch`, it keeps refreshing the final PO, diff file, and
outline file on each sync pass while you work. When a file is corrupt, watch
mode reports the error, restores the last valid file when possible, and keeps
running for the next pass.

`make sync-watch` now uses `watchdog` as its single watch implementation.
If the observer stops unexpectedly, the tool restarts the observer and keeps
watching.

#### 5. Edit Only `translation.md`

Open `translation.md` and edit only the `Translation (zh_Hant)` blocks.

- Do not change the UUID.
- Do not rename folders.
- Do not edit the `Source (en)` blocks unless you are intentionally fixing source text.
- Do not type translated text outside the `~~~text` fences.

If a field shows this machine-generated note:

```text
> Shared field: edit this translation in `shared_blocks/`.
```

do not translate that field inside `translation.md`. Instead, open
`translation/zh_Hant/tree/shared_blocks/` and edit the matching
`context.md` file there. `make sync` will copy that shared translation
back into every linked tree field. Shared nodes are also marked with `[shared]` inside
`translation/zh_Hant/tree/outline.md`. For a compact progress overview, use
`translation/zh_Hant/tree/shared_blocks_outline.md`.

Each file keeps fields in a stable order such as:

- `title`
- `label`
- `text`
- `advice`

#### 6. Check What Is Still Untranslated

```shell
make status
```

This shows:

- which folders still have untranslated fields
- the first few untranslated fields in tree order

#### 7. Run Translation Tests And Open A PR

Before running translation tests, make sure the generated PO and diff outputs
are up to date. If you are not already running `make sync-watch`, refresh them
with either:

```shell
make sync
```

or:

```shell
make sync-watch
```

Then run:

```shell
make test-translation
```

This verifies that:

- `translation/zh_Hant/tree` is structurally valid
- the checked-in tree and generated PO are still in sync
- the checked-in diff matches the current PO review
- the checked-in outline matches the current tree progress
- the checked-in `shared_blocks/` directory matches the current tree state
- the checked-in `shared_blocks_outline.md` matches the current tree state

In normal translation work, `make test-translation` should pass after
`make sync` or `make sync-watch`.

If the tests pass, open a pull request with your translation changes.

If the tests do not pass, please notify the developer or project maintainer
and report the problem instead of trying to work around it manually.

#### 8. Upload The Final PO (Legacy Path)

After the translation pull request has been merged, you can manually upload
`translation/zh_Hant/builds/final_translated.po` to:

`https://localize.ds-wizard.org/projects/knowledge-models/common-dsw-knowledge-model/zh_Hant/`

Use this path only when maintainers have explicitly decided that repository
translations should be pushed back to Localize/Weblate. It must not run on a
schedule.

For the zh-Hant migration workflow, prefer the reviewed-chapter migration
command described below. It produces a focused PO and report instead of
uploading the whole generated PO by hand.

### For Developers

This section is for maintaining the tooling and preparing final deliverables.

#### Show Available Targets

```shell
make help
```

#### Install Dev Tools

```shell
make install-dev
```

This installs the packages listed in `config/requirements.txt` into `.venv`.

#### Install Git Hooks

```shell
make install-hooks
```

This installs a local `pre-commit` hook so Ruff can fix imports and enforce
project formatting before each commit.

#### Auto-Format Python Code

```shell
make format
```

This runs Ruff autofixes and Ruff formatting for `src/` and `tests/`.

#### Check Formatting

```shell
make format-check
```

This verifies that Python files already match the repository formatter rules.

#### Check Python Syntax

```shell
make compile
```

This checks whether the Python files under `src/` can be compiled successfully.

#### Run Lint

```shell
make lint
```

This runs Ruff with the repository PEP8-style configuration from
`config/ruff.toml`.

#### Run Unit Tests

```shell
make test
```

This runs the pytest suite for:

- infrastructure and CLI behavior
- translation tree and PO consistency

#### One-Shot Reviewed Translation Migration To Localize

Use this only when repository translations are ahead of Localize/Weblate and
need to be migrated to the website. It is not meant to be a permanent
bidirectional sync path.

First refresh the Localize PO and rebuild the repository PO from the tree:

```shell
.venv/bin/python src/pull_localize_po.py \
  --repo-root /path/to/translation-repo \
  --config translation-config.yml

.venv/bin/python src/tree_to_po.py \
  --tree-dir /path/to/translation-repo/tree \
  --original-po /path/to/translation-repo/sources/localize/zh_Hant/latest.po \
  --out-po /path/to/translation-repo/builds/final_translated.po
```

Then prepare a dry-run migration report for the reviewed chapters:

```shell
.venv/bin/python src/migrate_reviewed_to_localize.py \
  --repo-root /path/to/translation-repo \
  --config translation-config.yml \
  --chapters 0004 0005 0006 \
  --fill-localize-blanks-from-repo
```

If the translation repository has not received `translation-config.yml` yet,
run the dry-run with explicit paths:

```shell
.venv/bin/python src/migrate_reviewed_to_localize.py \
  --repo-root /path/to/translation-repo \
  --chapters 0004 0005 0006 \
  --localize-po sources/localize/zh_Hant/latest.po \
  --repo-po builds/final_translated.po \
  --tree-dir tree \
  --fill-localize-blanks-from-repo
```

This writes:

- `reviews/localize_migration_upload.po`
- `reviews/localize_migration_report.json`

Review the report before uploading. To apply the migration, set
`LOCALIZE_API_TOKEN` and pass `--apply`:

```shell
LOCALIZE_API_TOKEN=... \
.venv/bin/python src/migrate_reviewed_to_localize.py \
  --repo-root /path/to/translation-repo \
  --config translation-config.yml \
  --chapters 0004 0005 0006 \
  --fill-localize-blanks-from-repo \
  --apply
```

The upload uses Weblate's `translate` method with
`conflicts=replace-translated`, so the migration PO updates existing
translations that are not approved while keeping the upload scoped to the
merged PO. If approved strings also need to be replaced, rerun with
`--conflicts replace-approved` using an account that has permission to do so.
After the migration is complete, the latest translation state should be
governed by Localize/Weblate and the repository should pull from it.

For Localize/Weblate PO exports without UUID-aware context, repeated identical
source strings share one translation. If a reviewed chapter and another
chapter need different translations for the same source string, Localize can
only keep one of them; prefer the reviewed chapter translation for the migration
and document the affected source strings.

#### Localize/Weblate To Git Sync

After the migration is complete, the latest translation state is governed by
Localize/Weblate. The translation repository mirrors it and provides
automation, visualization, reviewable history, generated tree artifacts, and
the final translated KM.

Use the high-level sync entry point for normal automation:

```shell
.venv/bin/python src/sync_from_localize.py \
  --host-repo /path/to/translation-repo \
  --tooling-repo /path/to/DSW_Translation_tool \
  --config translation-config.yml \
  --translation-root . \
  --target-ref master \
  --mode schedule
```

This command:

- downloads the current Localize/Weblate PO into
  `sources/localize/zh_Hant/latest.po`
- keeps the previous PO snapshot as `sources/localize/zh_Hant/base.po`
- force-refreshes `tree/` from the latest Localize/Weblate PO, so Git mirrors
  the website before any generated artifacts are rebuilt
- syncs `tree/`, `builds/final_translated.po`, review files, and
  `builds/final_translated.km`
- uses `latest-wins` for non-fuzzy Weblate changes when both Weblate and the
  repository changed the same string
- commits and pushes only Git repository changes

It never uploads repository translations back to Localize/Weblate.

#### Run Infrastructure Unit Tests

```shell
make test-infra
```

#### Run Translation Unit Tests

```shell
make test-translation
```

#### Auto-Sync Writer Workflows

The repository includes one active in-repo auto-sync workflow plus one
copy-ready external template:

- [.github/workflows/translation_auto_sync.yml](./.github/workflows/translation_auto_sync.yml)
  writes back to this repository's checked-in `translation/zh_Hant` tree.
- [examples/github-actions/translation_external_auto_sync_template.yml](./examples/github-actions/translation_external_auto_sync_template.yml)
  is the copy-ready auto-sync template for a dedicated translation-only
  repository. It intentionally lives outside `.github/workflows/` so it does
  not run inside this tooling repository.

The external translation workflow treats the latest Localize/Weblate state as
authoritative. Its policy is:

- they run on `schedule` at Asia/Taipei `09:00` and `21:00`
- they also run on `pull_request` targeting `master`
- scheduled runs pull Localize/Weblate and commit directly to `master`
- PR runs commit only for same-repository branches
- PR runs act as a sync gate: a merge candidate must include the latest
  Localize/Weblate translations before it reaches `master`
- fork PRs are validated by the normal test workflows, but the auto-writer
  skips any commit/push step
- bot-authored follow-up PR events are skipped to avoid recursive sync commits
- no workflow performs scheduled repository-to-Localize uploads

The high-level helper for external translation repositories is
[`src/sync_from_localize.py`](./src/sync_from_localize.py). It pulls the current
Localize/Weblate PO, re-exports the translation tree from that PO with existing
tree translations discarded, then delegates PO/KM generation, validation, and
Git commits to [`src/ci_sync_commit.py`](./src/ci_sync_commit.py). After
shared-string sync builds `builds/final_translated.po`, the CI helper also
builds `builds/final_translated.km` with the translated KM identity.

The auto-sync writer is intentionally aggressive when a checked-in translation
source file is malformed in CI:

- if `translation.md` or one canonical
  `shared_blocks/<group-id>/context.md` file cannot be parsed during sync
  and there is no local backup available in the CI checkout, the helper
  restores that file from `origin/master`
- after restoring the file, the helper reruns sync exactly once
- if validation still fails after that retry, the workflow stops and does not
  commit anything

This recovery policy is useful for keeping collaboration branches unblocked,
but it can overwrite malformed edits from the PR branch. In other words, it is
designed to recover the repository to the last known-good `master` state, not
to salvage partially broken translator edits.

#### Export Translation Tree

```shell
make export-tree
```

This writes a folder tree that mirrors the knowledge-model structure.

- Folder names use the node `title` / `label` / `name`.
- Nodes that only have `description` use the related `targetUuid` / `resourcePageUuid` node name as the folder label.
- Every node folder contains `_uuid.txt`.
- Translatable fields are grouped into a single `translation.md` per folder.
- The tree root also contains `outline.md` for hierarchy and progress browsing.
- The tree root also contains `shared_blocks/` as the canonical split shared-block source.
- `make sync` additionally refreshes `shared_blocks_outline.md` for compact shared-block progress review.
- Inside `translation.md`, each field is shown in a stable order such as `title -> label -> text -> advice`.
- Shared fields in `translation.md` are marked with a note that redirects translators to `shared_blocks/`.
- The export root also contains `_translation_tree.json` for validation and re-import.
- Re-running export preserves existing translations by default.

If you intentionally want to rebuild the tree from the supplied PO and discard current tree content:

```shell
make export-tree-force
```

This will show a warning and require typing `yes`.

#### Build PO From Translation Tree

```shell
make tree-to-po
```

This also stops and restores the affected `translation.md` if a fence is
broken or text appears outside fenced translation blocks.

#### Build KM From Final PO

```shell
make po-to-km
```

This rewrites `translation/zh_Hant/builds/final_translated.po` back into
`translation/zh_Hant/builds/final_translated.km` by updating the original
`files/dsw_root_2.7.0.km` bundle at the event fields that define the current
translatable text.

The generated KM is given a translated package identity so it can be imported
next to the official source KM without colliding with it. By default,
`dsw:root:2.7.0` becomes `dsw:root-zh-hant:2.7.0`, and the display name becomes
`Common DSW Knowledge Model (zh_Hant)`.

You can override the generated identity directly if needed:

```shell
python src/po_to_km.py \
  --output-organization-id local \
  --output-km-id root-zh-hant \
  --output-name "Common DSW Knowledge Model (zh_Hant)"
```

Empty `msgstr` values are treated as untranslated and keep the original KM
source text. This output is a translated KM bundle, not a DSW locale ZIP
package.

#### Review PO Differences

```shell
make review-po
```

This compares `translation/zh_Hant/builds/final_translated.po` with the original PO
template and writes a unified diff to
`translation/zh_Hant/reviews/final_translated.diff`.

Use this when you want to confirm that only `msgstr` values changed.

#### Validate Final Output

```shell
make validate
```

#### Optional Final Round-Trip Workflow

```shell
make workflow
```

This is only for a final smoke test or a full round-trip check.
You do not need to run it while translation is still in progress.

### Output Layout

The repository now keeps collaboration files and generated files under:

- `translation/zh_Hant/tree`
- `translation/zh_Hant/builds`
- `translation/zh_Hant/reviews`
- `translation/zh_Hant/reports`
- `translation/zh_Hant/backups` for local machine-managed safety copies
