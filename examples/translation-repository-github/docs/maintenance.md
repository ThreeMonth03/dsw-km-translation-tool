# GitHub-only translation maintenance

## Authority

Git is the only translation authority. There is no active Weblate component.
Do not add a Localize URL as a placeholder.

The source KM is pinned by `knowledge_model.upstream_ref` in
`translation-config.yml`. The tooling is also pinned. Update either dependency
through a reviewed pull request.

## First bootstrap

After the first source KM release is available:

```shell
git clone https://github.com/{{TOOLING_REPOSITORY}} tooling-repo
git -C tooling-repo checkout {{TOOLING_REF}}
make -C tooling-repo install-dev
tooling-repo/.venv/bin/dsw-km-sync-github-release --repo-root .
```

The command downloads the exact `knowledge_model.upstream_ref` GitHub Release,
verifies its `.sha256` sidecar and package ID, creates an empty Git-managed
catalog, and builds the editable tree and native locale PO. No manual asset
download is needed.

For a source KM update, change `upstream_ref`, `version`, and `bundle_path`
together in a pull-request branch, then run the same command. Translations are
carried only when the UUID, field, and English source text are unchanged.

## Routine edits

Edit only the Translation fenced blocks under `tree/`, then rebuild:

```shell
tooling-repo/.venv/bin/dsw-km-build-translation-repo --repo-root .
```

Commit the tree, catalog, review report, and build outputs together. Pull
requests rebuild them and fail if the checkout is not reproducible.

After CI passes, import `builds/final_translated.po` into the matching source
Knowledge Model with DSW's locale import. Do not import the source `.km` as a
translated package.

## Publish a Locale

Push a tag `km-<source KM version>-{{TARGET_LANGUAGE}}-r<revision>` on the clean,
validated tracking branch. Increment the translation revision for each
publication; the source KM version does not need to change. `tooling.ref` must
be a full commit SHA. The release workflow verifies the pinned source release,
rebuilds the PO, and requires a clean Git diff.

The new GitHub Release becomes Latest and contains a versioned PO, stable PO
alias, config, provenance manifest, release notes, and `SHA256SUMS`. Download
all assets and run `sha256sum -c SHA256SUMS` to verify them. Import only the PO
into DSW; never overwrite an existing release to publish a correction.

## Future Weblate cutover

If the DSW team later creates an official component, import the checked-in PO
once and switch authority in a dedicated cutover pull request. Never run Git
and Weblate as simultaneous writers.
