# Releases

The tooling, source KM, and translated locale have separate release versions.
A wording correction must not require publishing a new source KM.

Translation repositories use configuration schema 3. KM and PO artifact paths
are derived from the configured coordinates and language.

## Native Locale Releases

Translation repositories include **Publish Native KM Locale**, triggered after
successful Weblate sync, GitHub translation import, or KM update workflows.
It checks the tracking branch and chooses `locale-<language>-r<revision>` automatically.
For example, `locale-zh_Hant-r2` is the second locale revision. Revision numbers
advance independently of the context KM; do not include KM versions in tags.

Publication requires:

1. The alignment check confirms the repository matches Weblate and reproduces the final PO.
2. `tooling.ref` is a full reviewed commit SHA and the managed scaffold matches that checkout.
3. The source KM, editable tree, generated PO, and review outputs are committed and reproducible.

The planner compares usable, non-fuzzy translations with the newest published
locale. Documentation, PO headers, references, and newly empty entries do not
trigger a release. Changed or removed usable translations do. Existing tags are
never reused. **Run workflow** retries the same checks without requiring a tag;
unchanged translations produce a successful no-op. KM source differences are informational.

The workflow publishes exactly three assets: a versioned PO, `manifest.json`,
and `SHA256SUMS`. Only the PO is needed for DSW import. The manifest includes
the Weblate snapshot URL, original project/version header and checksum,
context KM coordinates/checksum, released PO checksum, translation/tooling
commits, language and accepted message counts. The manifest uses schema 2;
`context_knowledge_model` is test provenance, not a required catalog version. Release notes appear in the release page body. The configuration
is available in Git at the recorded translation commit.
Assets are uploaded to a draft before it is published as Latest. A failed upload
cannot become a published baseline; retries skip its reserved revision.
Never replace an existing tag or asset
to correct a translation; increment the locale revision.

Import the PO into the desired KM through DSW's native **Import locale** action,
available since DSW 4.33. Versions need not match: DSW looks up source strings
and falls back to source text when no translation matches. Before publishing,
CI checks syntax and language, then imports the PO in a disposable official DSW
instance. It verifies the PO round trip and source/translated language switching.
Import, questionnaire switching, page-load failures and unexpected resource-page
text block publication. Incomplete official POT coverage or source-language
fallback on resource pages produces a warning and a detailed report; partial
translations remain releasable.
See [Native Locale Verification](native-locale-verification.md).

Pull-request PO artifacts are temporary review downloads, not formal releases
or hosted DSW previews.

## Tooling Releases

1. Update the version in `pyproject.toml` and write concise user-facing notes in
   `docs/releases/<version>.md`.
2. Run `make check`, review the pull request, and merge it.
3. Tag the accepted commit as `v<version>` and push that tag.

**Release Tooling** checks the tag against the package version, runs the full
validation suite, and publishes the corresponding release notes. Use the source
checkout, including `examples/`, for repository scaffolding and maintenance.

For each downstream repository, change `tooling.ref` to the release's full
commit SHA, regenerate managed docs/workflows, and review that update in a
pull request. Updating a tool tag alone does not update downstream pins.

See [the command reference](command-reference.md) for local asset preparation.
Local preparation places the three uploadable files in `assets/` and writes
`release-notes.md` alongside that directory, outside the upload set.
