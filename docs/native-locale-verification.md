# Native Locale Verification

These checks answer different questions:

| Check | What it proves |
| --- | --- |
| PO validation | A nonempty catalog has valid syntax, language and native KM references; every referenced source string matches the KM |
| Official POT coverage | Which official DSW source messages are missing, empty, fuzzy or extra in the PO |
| Upstream source catalog | Whether Weblate's shared repository POT includes the official source messages for the configured KM version |
| Browser acceptance | Official DSW imports the PO, returns the same file and renders a translated chapter after language switching |

A PO can pass import validation while leaving some official source messages in
English. A fully translated Weblate catalog does not necessarily cover the
entire official POT. Coverage uses gettext context and source text as message
identity, not the spelling of UUID references.

Translation-tree inputs retain their source references, including the current
official `entity/UUID/field` format. Existing snapshots do not need rewriting.
Refresh catalogs from Weblate together with their matching official KM; do not
rewrite source messages or relabel a bundle to bypass validation.

## Review in Actions

In a translation repository, open **KM Translation Operations**, then download
the `native-dsw-review` artifact. It includes:

- `coverage.md` and `coverage.json`: counts and the full missing source strings.
- `official.pot`: the template exported by DSW for this exact source KM.
- `source-catalog/`: upstream POT snapshot, commit, checksums and source difference
  reports in `source-catalog.md` and `source-catalog.json`.
- `locale-imported.png` and `questionnaire-*.png`: real browser screenshots.
- `result.json`: test outcome, input PO checksum, DSW image versions, and coverage
  status/counts with a link to `coverage.json`. Full coverage details are stored
  only in the dedicated coverage reports.
- `failure.png`, when a browser check fails.

Artifacts are retained for 14 days. Screenshots check a translated chapter title;
they are not a review of every question or a hosted, interactive preview.
Download the PR's `native-locale-<head SHA>` artifact to review other changes in
your own test DSW instance.

The check runs for translation pull requests, tracking-branch pushes, manual
runs and daily scheduled verification. The daily run also checks updates made
by automation, whose Git pushes do not start another Actions workflow.
Both tooling and locale release workflows run acceptance before publishing.
Only **KM Translation Operations** enables the live upstream source audit;
releases validate their pinned inputs without depending on today's upstream POT.

Import, download, malformed POT and browser failures fail CI. A valid upstream
POT for another version reports **waiting-for-km** without comparing coverage
across versions. Missing, empty, fuzzy or extra entries make coverage
**incomplete** and emit a warning, without
blocking a usable partial locale. This check reports gaps; it does not change
translations, upload to Weblate, or maintain an exceptions list.

## Source Catalog Updates

The source audit reads `messages.pot` from the default branch of the public
GitHub repository configured by `localize.repository`. It fetches a temporary
bare snapshot without executing upstream code and records the exact commit.
Coverage comparison requires the upstream POT version to match the configured
KM. An empty, invalid or unrecognized-package POT fails the audit. A valid POT for another version is
reported as **waiting-for-km** without comparing its messages to the current KM.
An unset repository is reported as
**not-configured**, never as complete coverage.

Read `source-catalog/source-catalog.md` in the Actions artifact:

- **aligned**: both POTs contain the same gettext message identities.
- **waiting-for-km**: upstream identifies a different KM version; retain the verified pair.
- **additions-only**: the official export contains sources absent from upstream.
- **review-required**: upstream also contains sources absent from the official
  export. Review source edits, removals or a different source model before proceeding.

Source differences emit warnings. Download or validation errors fail the source
audit separately from browser acceptance. The audit checks the repository POT,
not the live Weblate units: even an aligned POT may still need merging into the
language PO files before translators see new entries.

For a confirmed extraction gap, submit one upstream PR with the extraction fix,
tests and regenerated POT. Reuse that PR for follow-up findings rather than
opening duplicates on every scheduled run. Official maintainers decide whether
to accept it and configure Weblate's
[Update PO files to match POT](https://docs.weblate.org/en/latest/admin/addons.html#update-po-files-to-match-pot-msgmerge)
add-on or equivalent upstream automation. POT updates alone do not guarantee
existing language PO files are refreshed.

Before an upstream merge, verify that unchanged message/context pairs preserve
every language's translations and review flags. New sources can add untranslated
entries to every language and lower completion percentages. Changed or removed
sources require explicit review. Do not replace language files with an empty POT.
Our scheduled jobs do not upload source strings, change Weblate settings, open
upstream PRs automatically or maintain a separate canonical POT. After the
official PO catalogs update, normal Weblate-to-Git sync picks up the new entries.

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
source language and verifies persisted rendering after reload. Containers and
volumes are removed on success or failure. Other Docker stacks are untouched.
It cannot target an existing DSW server. Reports contain no login tokens.

The tested server/client image versions are pinned in
`tests/native_locale/compose.yml`. Upgrade these together and rerun acceptance;
they are independent of the `dsw-models` Python dependency.
The disposable object store uses the upstream MinIO and client images from Quay.
