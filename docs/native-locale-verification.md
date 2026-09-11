# Native Locale Verification

Three checks answer different questions:

| Check | What it proves |
| --- | --- |
| PO validation | Catalog syntax, language and existing KM references are valid |
| Official POT coverage | Which official DSW source messages are missing, empty, fuzzy or extra in the PO |
| Browser acceptance | Official DSW imports the PO, returns the same file and renders a translated chapter after language switching |

A PO can pass import validation while leaving some official source messages in
English. A fully translated Weblate catalog does not necessarily cover the
entire official POT. Coverage uses gettext context and source text as message
identity, not the spelling of UUID references.

## Review in Actions

In a translation repository, open **KM Translation Operations**, then download
the `native-dsw-review` artifact. It includes:

- `coverage.md` and `coverage.json`: counts and the full missing source strings.
- `official.pot`: the template exported by DSW for this exact source KM.
- `locale-imported.png` and `questionnaire-*.png`: real browser screenshots.
- `result.json`: test outcome, input PO checksum and DSW image versions.
- `failure.png`, when a browser check fails.

Artifacts are retained for 14 days. Screenshots check a translated chapter title;
they are not a review of every question or a hosted, interactive preview.
Download the PR's `native-locale-<head SHA>` artifact to review other changes in
your own test DSW instance.

The check runs for translation pull requests, tracking-branch pushes, manual
runs and daily scheduled verification. The daily run also checks updates made
by automation, whose Git pushes do not start another Actions workflow.
Both tooling and locale release workflows run acceptance before publishing.

Import, download, malformed POT and browser failures fail CI. Missing, empty,
fuzzy or extra entries make coverage **incomplete** and emit a warning, without
blocking a usable partial locale. This check reports gaps; it does not change
translations, upload to Weblate, or maintain an exceptions list.

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
