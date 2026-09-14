# Releases

The tooling, source KM, and translated locale have separate release versions.
A wording correction must not require publishing a new source KM.

Translation repositories use configuration schema 3. KM and PO artifact paths
are derived from the configured coordinates and language.

## Native Locale Releases

Translation repositories include **Publish Native KM Locale**.
Push `locale-<language>-r<revision>` from the validated tracking branch.
For example, `locale-zh_Hant-r2` is the second locale revision. Revision numbers
advance independently of the context KM; do not include KM versions in tags.

Before tagging:

1. Wait for translation import/sync jobs to finish. The alignment report must
   show that the repository matches Weblate and reproduces the final PO.
2. Pin `tooling.ref` to a full reviewed commit SHA and regenerate the scaffold
   using that exact tool checkout.
3. Confirm the source KM, editable tree, generated PO, and review outputs are
   committed and reproducible. KM source differences are informational.

The workflow publishes exactly three assets: a versioned PO, `manifest.json`,
and `SHA256SUMS`. Only the PO is needed for DSW import. The manifest includes
the Weblate snapshot URL, original project/version header and checksum,
context KM coordinates/checksum, released PO checksum, translation/tooling
commits, language and accepted message counts. The manifest uses schema 2;
`context_knowledge_model` is test provenance, not a required catalog version. Release notes appear in the release page body. The configuration
is available in Git at the recorded translation commit.
The successful release becomes Latest. Never replace an existing tag or asset
to correct a translation; increment the locale revision.

Import the PO into the desired KM through DSW's native **Import locale** action,
available since DSW 4.33. Versions need not match: DSW looks up source strings
and falls back to source text when no translation matches. Before publishing,
CI checks syntax and language, then imports the PO in a disposable official DSW
instance. It verifies the PO round trip and source/translated language switching.
Import or rendering failures block publication. Incomplete official POT coverage
produces a warning and a detailed report; partial translations remain releasable.
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
