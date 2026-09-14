# Native Locale Verification

These checks answer different questions:

| Check | What it proves |
| --- | --- |
| PO validation | A nonempty catalog has valid syntax, language and native reference syntax |
| Official POT coverage | Which official DSW source messages are missing, empty, fuzzy or extra in the PO |
| Upstream source catalog | How the authoritative upstream POT differs from the context KM export |
| Browser acceptance | Official DSW imports the PO, returns the same file and renders a translated chapter after language switching |
| Resource-page rendering | Whether standalone resource pages display matching PO translations or fall back to source text |

A PO can pass import validation while leaving some official source messages in
English. A fully translated Weblate catalog does not necessarily cover the
entire official POT. Coverage uses gettext context and source text as message
identity, not the spelling of UUID references.

Translation-tree inputs retain their source references, including the current
official `entity/UUID/field` format. Existing snapshots do not need rewriting.
Refresh catalogs from Weblate independently of KM releases. The KM provides
hierarchy and a browser-test target; source differences never block the catalog.
Entities absent from the KM are exported as top-level translation folders,
without invented parent relationships. Source text always comes from the PO.

## Review in Actions

In a translation repository, open **KM Translation Operations**, then download
the `native-dsw-review` artifact. It includes:

- `coverage.md` and `coverage.json`: counts and the full missing source strings.
- `official.pot`: the template exported by DSW for this exact source KM.
- `source-catalog/`: upstream POT snapshot, commit, checksums and source difference
  reports in `source-catalog.md` and `source-catalog.json`.
- `locale-imported.png` and `questionnaire-*.png`: real browser screenshots.
- `resource-pages.md`, `resource-pages.json` and `resource-*.png`: resource-page
  rendering counts, per-field source/translation/displayed text and screenshots.
- `result.json`: test outcome, input PO checksum, DSW image versions, and coverage
  status/counts with a link to `coverage.json`, plus a separate resource-page
  outcome. `passed-with-warnings` means the import checks passed but coverage
  or resource-page rendering was incomplete or not checked. Full details are
  stored only in their dedicated reports.
- `failure.png`, when a browser check fails.

Artifacts are retained for 14 days. Screenshots check a translated chapter title
and resource pages with eligible translations; they are not a review of every
question or a hosted, interactive preview.
Download the PR's `native-locale-<head SHA>` artifact to review other changes in
your own test DSW instance.

The check runs for translation pull requests, tracking-branch pushes, manual
runs and daily scheduled verification. The daily run also checks updates made
by automation, whose Git pushes do not start another Actions workflow.
Both tooling and locale release workflows run acceptance before publishing.
Only **KM Translation Operations** enables the live upstream source audit;
releases validate their pinned inputs without depending on today's upstream POT.

Import, download, malformed POT and browser failures fail CI. Source differences
and missing, empty, fuzzy or extra entries emit warnings without blocking a
usable partial locale. Comparisons include both catalog identities even when
the upstream version differs from the context KM. This check reports gaps; it does not change
translations, upload to Weblate, or maintain an exceptions list.

## Resource Pages

After verifying questionnaire switching, the check selects the target language
in project settings and opens standalone resource pages in the same browser.
Candidates are selected automatically from the official test-KM POT and input
PO by exact source text and gettext context. Empty, fuzzy, absent and visibly
unchanged translations cannot demonstrate localization and are not candidates.
Their coverage remains visible in the separate POT report.

Titles and Markdown content are compared as normalized rendered text, not HTML
markup, layout or link destinations. Each checked field is **translated**,
**source** (the original text is still displayed), or **unexpected**.
The resource-page outcome is **passed** only when every checked field displays
its translation. No candidates means **not-checked**, never a pass.

Source fallback produces an **incomplete** warning without blocking an importable
PO. Unexpected text or a page that fails to load fails CI. Read the separate
resource-page outcome even when import and questionnaire checks pass; project
language selection alone does not prove that standalone pages use that language.

## Source Catalog Updates

The source audit reads `messages.pot` from the default branch of the public
GitHub repository configured by `localize.repository`. It fetches a temporary
bare snapshot without executing upstream code and records the exact commit.
An empty, invalid or unrecognized-package POT fails the audit. Source version
differences are reported, not treated as a reason to wait. An unset repository is reported as
**not-configured**, never as complete coverage.

Read `source-catalog/source-catalog.md` in the Actions artifact:

- **aligned**: both POTs contain the same gettext message identities.
- **different**: the two catalogs contain different source messages. The report
  lists sources found only in either catalog. Different KM versions can naturally
  produce these differences; this is not evidence of an upstream extraction bug.

Source differences emit warnings. Download or validation errors fail the source
audit separately from browser acceptance. The audit checks the repository POT,
not the live Weblate units: even an aligned POT may still need merging into the
language PO files before translators see new entries.

Official maintainers own extraction and POT-to-PO updates. This repository does
not upload sources, change other languages, open upstream PRs automatically or
maintain its own canonical POT. Normal synchronization consumes the official
language PO, including additions, removals, empty translations and fuzzy flags.
An updated POT alone does not guarantee Weblate has updated every language PO.
Reports describe differences but do not preserve translations removed upstream.

## Run Locally

Use Docker Engine with Compose, OpenSSL and the tooling checkout. No DSW account
or production credentials are needed.

```shell
make install-dev
.venv/bin/python -m pip install -e '.[browser]'
.venv/bin/python -m playwright install --with-deps chromium
.venv/bin/python tests/native_locale/check.py \
  --repo-root /path/to/translation-repository \
  --out /tmp/native-dsw-review
```

Use an empty output directory. Omit `--repo-root` to test the tooling's checked-in
KM and PO fixtures. Rebuild the translation repository first if you want to test
unbuilt Markdown edits.

The check starts a uniquely named stack with loopback-only, dynamically assigned
ports, fresh data and disposable example users. It exports the POT from that
instance, imports the PO through the browser, switches source → translated →
source language and verifies persisted rendering after reload. It then restores
the target language for resource-page review. Containers and
volumes are removed on success or failure. Other Docker stacks are untouched.
It cannot target an existing DSW server. Reports contain no login tokens.

The tested server/client image versions are pinned in
`tests/native_locale/compose.yml`. Upgrade these together and rerun acceptance;
they are independent of the `dsw-models` Python dependency.
The disposable object store uses the upstream MinIO and client images from Quay.
