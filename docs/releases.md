# Releases

The tooling, source KM, and translated locale have separate release versions.
A wording correction must not require publishing a new source KM.

## Native Locale Releases

All translation repository profiles include **Publish Native KM Locale**.
Push `km-<source KM version>-<language>-r<revision>` from the validated tracking
branch. For example, `km-2.7.0-zh_Hant-r2` publishes the second translation
revision for the same KM as `km-2.7.0-zh_Hant-r1`.

Before tagging:

1. Wait for translation import/sync to finish. For Weblate repositories, confirm
   the alignment report passes.
2. Pin `tooling.ref` to a full reviewed commit SHA and regenerate the scaffold
   using that exact tool checkout.
3. Confirm the source KM, editable tree, generated PO, and review outputs are
   committed and reproducible. For GitHub-authoritative repositories, the
   pinned source must also pass its Git or Release verification.

The workflow publishes a versioned PO, stable PO alias, config, provenance
manifest, release notes, and `SHA256SUMS`. The manifest includes source KM and
PO checksums, translation and tooling commits, language, and message counts.
The successful release becomes Latest. Never replace an existing tag or asset
to correct a translation; increment the locale revision.

The PO is imported into the matching source KM through DSW's native **Import
locale** action, available since DSW 4.33. CI checks gettext syntax, language,
and KM references locally; it does not perform a server-side DSW import.

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
