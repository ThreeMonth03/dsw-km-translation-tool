VENV_DIR ?= .venv
VENV_PYTHON := $(VENV_DIR)/bin/python
BOOTSTRAP_PYTHON ?= python3
PYTHON ?= $(VENV_PYTHON)
PIP := $(PYTHON) -m pip

PO ?= files/knowledge-models-common-dsw-knowledge-model-zh_Hant.po
MODEL ?= files/dsw_root_2.7.0.km
SOURCE_LANG ?= en
TARGET_LANG ?= zh_Hant
OUTPUT_ROOT ?= translation/$(TARGET_LANG)
TREE_DIR ?= $(OUTPUT_ROOT)/tree
FINAL_PO ?= $(OUTPUT_ROOT)/builds/final_translated.po
FINAL_KM ?= $(OUTPUT_ROOT)/builds/final_translated.km
REPORT ?= $(OUTPUT_ROOT)/reports/final_report.json
TREE_JSON ?= $(OUTPUT_ROOT)/reports/tree_snapshot.json
REVIEW_DIFF ?= $(OUTPUT_ROOT)/reviews/final_translated.diff
OUTLINE_MD ?= $(TREE_DIR)/outline.md
SHARED_BLOCKS_OUTLINE_MD ?= $(TREE_DIR)/shared_blocks_outline.md
REVIEW_FLAGS ?=
PO_TO_KM_FLAGS ?=
STATUS_LIMIT ?= 5
SYNC_GROUP ?= shared-block
LOCALIZE_PO ?= sources/localize/zh_Hant/latest.po
LOCALIZE_STATUS_JSON ?= reviews/localize_status_report.json
LOCALIZE_STATUS_MD ?= reviews/localize_status_report.md
WEBLATE_CHECK_QUERY ?= has:check
WEBLATE_CHECKS_JSON ?= reviews/weblate_checks_report.json
WEBLATE_CHECKS_MD ?= reviews/weblate_checks_report.md
ALIGNMENT_JSON ?= reviews/localize_alignment_report.json
ALIGNMENT_MD ?= reviews/localize_alignment_report.md
ALIGNMENT_ARTIFACT_DIR ?= reviews/localize_alignment_artifacts
KM_DISCOVERY_JSON ?= reviews/km_version_discovery.json
KM_DISCOVERY_MD ?= reviews/km_version_discovery.md
KM_AUTO_UPDATE_JSON ?= reviews/km_auto_update_report.json
KM_AUTO_UPDATE_MD ?= reviews/km_auto_update_report.md
TRANSLATION_REPO_DIR ?=
TRANSLATION_CONFIG ?= translation-config.yml
TRACKING_BRANCH ?= master
TARGET_BRANCH ?=
RESTORE_SOURCE_REF ?= origin/$(TRACKING_BRANCH)
SPHINXBUILD ?= $(PYTHON) -m sphinx
SPHINXOPTS ?= -W --keep-going
DOCS_SOURCE ?= docs/sphinx
DOCS_BUILD ?= docs/sphinx/_build/html

.PHONY: help help-all require-translation-repo require-target-branch
.PHONY: venv install-dev install-hooks check compile format format-check lint
.PHONY: test test-infra test-translation docs docs-clean
.PHONY: repo-validate repo-pull-po repo-status repo-checks repo-align
.PHONY: repo-sync repo-sync-branch repo-km-status repo-km-pull repo-km-update
.PHONY: export-tree export-tree-force status localize-status sync sync-watch
.PHONY: tree-to-po po-to-km review-po validate workflow

venv: $(VENV_PYTHON)

$(VENV_PYTHON):
	$(BOOTSTRAP_PYTHON) -m venv $(VENV_DIR)

help:
	@printf '%s\n' \
	'Common maintainer targets:' \
	'  install-dev        Create $(VENV_DIR) and install dev dependencies' \
	'  check              Run format check, lint, compile, tests, docs, and git diff --check' \
	'  docs               Build Sphinx docs into $(DOCS_BUILD)' \
	'  format             Auto-fix imports/style and format Python files' \
	'' \
	'Translation repository targets; set TRANSLATION_REPO_DIR=/path/to/repo:' \
	'  repo-validate      Validate translation-config.yml' \
	'  repo-status        Report checked-in Weblate PO health' \
	'  repo-checks        Query Weblate quality checks' \
	'  repo-align         Verify Weblate/tree/final PO/final KM alignment' \
	'  repo-sync          Writer: pull Weblate, rebuild outputs, commit/push if changed' \
	'  repo-km-status     Report whether the Registry has a newer KM' \
	'  repo-km-update     Writer: update to latest KM only after validation passes' \
	'' \
	'Local translation-tree development targets:' \
	'  export-tree        Export PO + model into $(TREE_DIR)' \
	'  sync               Sync shared strings and rebuild $(FINAL_PO)' \
	'  status             Show untranslated fields from $(TREE_DIR)' \
	'  workflow           Run the optional end-to-end smoke workflow' \
	'' \
	'Run `make help-all` for lower-level targets and variables.'

help-all:
	@printf '%s\n' \
	'All targets:' \
	'  venv               Create $(VENV_DIR) when it does not exist' \
	'  install-dev        Install local dev dependencies from config/requirements.txt' \
	'  install-hooks      Install local git pre-commit hooks' \
	'  check              Run all local quality gates' \
	'  compile            Run Python syntax compilation checks' \
	'  format             Auto-fix imports/style and format Python files' \
	'  format-check       Check formatting without modifying files' \
	'  lint               Run ruff lint checks' \
	'  test               Run all pytest suites' \
	'  test-infra         Run infrastructure/CLI pytest suites' \
	'  test-translation   Run translation consistency pytest suites' \
	'  docs               Build Sphinx docs into $(DOCS_BUILD)' \
	'  docs-clean         Remove generated Sphinx docs' \
	'  repo-validate      Validate translation-config.yml in TRANSLATION_REPO_DIR' \
	'  repo-pull-po       Refresh sources/localize/ in TRANSLATION_REPO_DIR' \
	'  repo-status        Report checked-in Weblate PO health in TRANSLATION_REPO_DIR' \
	'  repo-checks        Query Weblate quality checks for TRANSLATION_REPO_DIR' \
	'  repo-align         Verify output alignment in TRANSLATION_REPO_DIR' \
	'  repo-sync          Writer: sync Weblate to Git in TRANSLATION_REPO_DIR' \
	'  repo-sync-branch   Writer: sync Weblate to TARGET_BRANCH for PR repair' \
	'  repo-km-status     Discover KM Registry versions for TRANSLATION_REPO_DIR' \
	'  repo-km-pull       Writer: refresh the configured source KM bundle' \
	'  repo-km-update     Writer: guarded latest-KM update for TRANSLATION_REPO_DIR' \
	'  export-tree        Export PO + model into $(TREE_DIR) and refresh shared-block files' \
	'  export-tree-force  Force rebuild $(TREE_DIR)' \
	'  status             Show untranslated fields from $(TREE_DIR)' \
	'  localize-status    Report Localize/Weblate PO status from $(LOCALIZE_PO)' \
	'  sync               Sync shared strings and refresh $(FINAL_PO)' \
	'  sync-watch         Watch editable inputs with watchdog' \
	'  tree-to-po         Build $(FINAL_PO) from $(TREE_DIR)' \
	'  po-to-km           Build $(FINAL_KM) from $(FINAL_PO) + $(MODEL)' \
	'  review-po          Review how $(FINAL_PO) differs from $(PO)' \
	'  validate           Validate $(FINAL_PO) against $(MODEL)' \
	'  workflow           Run the optional end-to-end smoke workflow'

require-translation-repo:
	@if [ -z "$(TRANSLATION_REPO_DIR)" ]; then \
		printf '%s\n' 'Set TRANSLATION_REPO_DIR=/path/to/dsw-root-locales-zh_Hant' >&2; \
		exit 2; \
	fi

require-target-branch:
	@if [ -z "$(TARGET_BRANCH)" ]; then \
		printf '%s\n' 'Set TARGET_BRANCH=<same-repository-branch-name>' >&2; \
		exit 2; \
	fi

install-dev: venv
	$(PIP) install -r config/requirements.txt

install-hooks: venv
	$(PYTHON) -m pre_commit install

check: format-check lint compile test docs
	git diff --check

compile: venv
	$(PYTHON) -m compileall -q src tests

format: venv
	$(PYTHON) -m ruff check --config config/ruff.toml --fix src tests
	$(PYTHON) -m ruff format --config config/ruff.toml src tests

format-check: venv
	$(PYTHON) -m ruff format --check --config config/ruff.toml src tests

lint: venv
	$(PYTHON) -m ruff check --config config/ruff.toml src tests

test: test-infra test-translation

test-infra: venv
	$(PYTHON) -m pytest tests/infra

test-translation: venv
	$(PYTHON) -m pytest tests/translation

docs: venv
	$(SPHINXBUILD) $(SPHINXOPTS) -b html $(DOCS_SOURCE) $(DOCS_BUILD)

docs-clean:
	rm -rf docs/sphinx/_build

repo-validate: venv require-translation-repo
	$(PYTHON) src/validate_translation_config.py \
		--config "$(TRANSLATION_REPO_DIR)/$(TRANSLATION_CONFIG)"

repo-pull-po: venv require-translation-repo
	$(PYTHON) src/pull_localize_po.py \
		--repo-root "$(TRANSLATION_REPO_DIR)" \
		--config "$(TRANSLATION_CONFIG)"

repo-status: venv require-translation-repo
	$(PYTHON) src/report_localize_status.py \
		--po "$(TRANSLATION_REPO_DIR)/$(LOCALIZE_PO)" \
		--json-out "$(TRANSLATION_REPO_DIR)/$(LOCALIZE_STATUS_JSON)" \
		--details-out "$(TRANSLATION_REPO_DIR)/$(LOCALIZE_STATUS_MD)"

repo-checks: venv require-translation-repo
	$(PYTHON) src/report_weblate_checks.py \
		--repo-root "$(TRANSLATION_REPO_DIR)" \
		--config "$(TRANSLATION_CONFIG)" \
		--query "$(WEBLATE_CHECK_QUERY)" \
		--json-out "$(TRANSLATION_REPO_DIR)/$(WEBLATE_CHECKS_JSON)" \
		--details-out "$(TRANSLATION_REPO_DIR)/$(WEBLATE_CHECKS_MD)" \
		--allow-api-failure

repo-align: venv require-translation-repo
	$(PYTHON) src/report_alignment_status.py \
		--repo-root "$(TRANSLATION_REPO_DIR)" \
		--config "$(TRANSLATION_CONFIG)" \
		--json-out "$(TRANSLATION_REPO_DIR)/$(ALIGNMENT_JSON)" \
		--details-out "$(TRANSLATION_REPO_DIR)/$(ALIGNMENT_MD)" \
		--artifact-dir "$(TRANSLATION_REPO_DIR)/$(ALIGNMENT_ARTIFACT_DIR)" \
		--fail-on-mismatch

repo-sync: venv require-translation-repo
	$(PYTHON) src/sync_from_localize.py \
		--host-repo "$(TRANSLATION_REPO_DIR)" \
		--tooling-repo "$(CURDIR)" \
		--config "$(TRANSLATION_CONFIG)" \
		--translation-root . \
		--target-ref "$(TRACKING_BRANCH)" \
		--mode schedule

repo-sync-branch: venv require-translation-repo require-target-branch
	$(PYTHON) src/sync_from_localize.py \
		--host-repo "$(TRANSLATION_REPO_DIR)" \
		--tooling-repo "$(CURDIR)" \
		--config "$(TRANSLATION_CONFIG)" \
		--translation-root . \
		--target-ref "$(TARGET_BRANCH)" \
		--restore-source-ref "$(RESTORE_SOURCE_REF)" \
		--mode pull_request

repo-km-status: venv require-translation-repo
	$(PYTHON) src/discover_km_versions.py \
		--repo-root "$(TRANSLATION_REPO_DIR)" \
		--config "$(TRANSLATION_CONFIG)" \
		--report "$(KM_DISCOVERY_JSON)" \
		--details-out "$(KM_DISCOVERY_MD)"

repo-km-pull: venv require-translation-repo
	$(PYTHON) src/pull_km_bundle.py \
		--repo-root "$(TRANSLATION_REPO_DIR)" \
		--config "$(TRANSLATION_CONFIG)"

repo-km-update: venv require-translation-repo
	$(PYTHON) src/sync_latest_km.py \
		--repo-root "$(TRANSLATION_REPO_DIR)" \
		--tooling-repo "$(CURDIR)" \
		--config "$(TRANSLATION_CONFIG)" \
		--target-ref "$(TRACKING_BRANCH)" \
		--report "$(TRANSLATION_REPO_DIR)/$(KM_AUTO_UPDATE_JSON)" \
		--details-out "$(TRANSLATION_REPO_DIR)/$(KM_AUTO_UPDATE_MD)" \
		--skip-without-token

export-tree: venv
	$(PYTHON) src/po_json_tree.py \
		--po $(PO) \
		--json $(MODEL) \
		--out-dir $(TREE_DIR) \
		--shared-blocks-dir-out $(TREE_DIR)/shared_blocks \
		--source-lang $(SOURCE_LANG) \
		--target-lang $(TARGET_LANG)

export-tree-force: venv
	$(PYTHON) src/po_json_tree.py \
		--po $(PO) \
		--json $(MODEL) \
		--out-dir $(TREE_DIR) \
		--shared-blocks-dir-out $(TREE_DIR)/shared_blocks \
		--source-lang $(SOURCE_LANG) \
		--target-lang $(TARGET_LANG) \
		--force

status: venv
	$(PYTHON) src/translation_status.py \
		--tree-dir $(TREE_DIR) \
		--source-lang $(SOURCE_LANG) \
		--target-lang $(TARGET_LANG) \
		-k $(STATUS_LIMIT)

localize-status: venv
	$(PYTHON) src/report_localize_status.py \
		--po $(LOCALIZE_PO) \
		--json-out $(LOCALIZE_STATUS_JSON)

sync: venv
	$(PYTHON) src/sync_shared_strings.py \
		--tree-dir $(TREE_DIR) \
		--original-po $(PO) \
		--out-po $(FINAL_PO) \
		--diff-out $(REVIEW_DIFF) \
		--outline-out $(OUTLINE_MD) \
		--shared-blocks-dir-out $(TREE_DIR)/shared_blocks \
		--shared-blocks-outline-out $(SHARED_BLOCKS_OUTLINE_MD) \
		--source-lang $(SOURCE_LANG) \
		--target-lang $(TARGET_LANG) \
		--group-by $(SYNC_GROUP)

sync-watch: venv
	$(PYTHON) src/sync_shared_strings.py \
		--tree-dir $(TREE_DIR) \
		--original-po $(PO) \
		--out-po $(FINAL_PO) \
		--diff-out $(REVIEW_DIFF) \
		--outline-out $(OUTLINE_MD) \
		--shared-blocks-dir-out $(TREE_DIR)/shared_blocks \
		--shared-blocks-outline-out $(SHARED_BLOCKS_OUTLINE_MD) \
		--source-lang $(SOURCE_LANG) \
		--target-lang $(TARGET_LANG) \
		--group-by $(SYNC_GROUP) \
		--watch

tree-to-po: venv
	$(PYTHON) src/tree_to_po.py \
		--tree-dir $(TREE_DIR) \
		--original-po $(PO) \
		--out-po $(FINAL_PO) \
		--source-lang $(SOURCE_LANG) \
		--target-lang $(TARGET_LANG)

po-to-km: venv
	$(PYTHON) src/po_to_km.py \
		--translated-po $(FINAL_PO) \
		--original-km $(MODEL) \
		--out-km $(FINAL_KM) \
		--source-lang $(SOURCE_LANG) \
		--target-lang $(TARGET_LANG) \
		$(PO_TO_KM_FLAGS)

review-po: venv
	$(PYTHON) src/review_po_changes.py \
		--original-po $(PO) \
		--generated-po $(FINAL_PO) \
		--diff-out $(REVIEW_DIFF) \
		$(REVIEW_FLAGS) \
		--source-lang $(SOURCE_LANG) \
		--target-lang $(TARGET_LANG)

validate: venv
	$(PYTHON) src/po_json_tree.py \
		--po $(FINAL_PO) \
		--json $(MODEL) \
		--report-out $(REPORT) \
		--source-lang $(SOURCE_LANG) \
		--target-lang $(TARGET_LANG)

workflow: venv
	$(PYTHON) src/translate_workflow.py \
		--po $(PO) \
		--json $(MODEL) \
		--tree-dir $(TREE_DIR) \
		--final-po $(FINAL_PO) \
		--report-out $(REPORT) \
		--source-lang $(SOURCE_LANG) \
		--target-lang $(TARGET_LANG)
