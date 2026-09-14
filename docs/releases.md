# Releases

The tooling, source KM, and translated locale have separate release versions.
A wording correction must not require publishing a new source KM.

Translation repositories use configuration schema 3. KM and PO artifact paths
are derived from the configured coordinates and language.

## Native Locale Releases

Translation repositories include **Publish Native KM Locale**.
Push `km-<source KM version>-<language>-r<revision>` from the validated tracking
branch. For example, `km-2.7.0-zh_Hant-r2` publishes the second translation
revision for the same KM as `km-2.7.0-zh_Hant-r1`.

Before tagging:

1. Wait for translation import/sync jobs to finish and review the alignment
   report. `aligned` confirms the repository matches Weblate. `waiting-for-km`
   permits a release of the existing verified KM/PO pair only when local
   integrity checks pass; it does not include pending upstream translations.
2. Pin `tooling.ref` to a full reviewed commit SHA and regenerate the scaffold
   using that exact tool checkout.
3. Confirm the source KM, editable tree, generated PO, and review outputs are
   committed and reproducible against the configured Registry KM.

The workflow publishes exactly three assets: a versioned PO, `manifest.json`,
and `SHA256SUMS`. Only the PO is needed for DSW import. The manifest includes
source KM and PO checksums, translation and tooling commits, language, and
message counts. Release notes appear in the release page body. The configuration
is available in Git at the recorded translation commit.
The successful release becomes Latest. Never replace an existing tag or asset
to correct a translation; increment the locale revision.

The PO is imported into the matching source KM through DSW's native **Import
locale** action, available since DSW 4.33. Before publishing, CI checks syntax,
language and KM references, then imports the PO in a disposable official DSW
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
