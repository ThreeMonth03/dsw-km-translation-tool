# First-Time Maintainer Guide

Use this page when you need to understand the repository before changing code
or operating a translation sync.

## Mental Model

For production zh-Hant work, Localize/Weblate owns the latest translation text.
This tooling turns that website state into files that can be reviewed, tested,
and committed in Git:

```text
Localize/Weblate PO -> tree/ -> final PO -> translated KM -> Git commit
```

The tooling repository contains reusable code, tests, workflow templates, and
documentation. A dedicated translation repository contains the actual
translation config and generated translation output files.

## First Hour

1. Read [Architecture](architecture.md) to learn which layer owns each
   behavior.
2. Read [Command Reference](command-reference.md) to identify whether a command
   is read-only or writes generated files.
3. Read the relevant runbook before touching production automation:
   [Localize Sync Runbook](localize-sync-runbook.md) for Weblate-to-Git sync, or
   [KM Update Runbook](km-update-runbook.md) for source KM updates.
4. Set up the tooling repo locally:

   ```shell
   make install-dev
   make check
   ```

5. When changing command behavior, start from the packaged CLI module in
   [`src/dsw_km_translation_tool/cli/`][cli-dir], then follow it into
   [`src/dsw_km_translation_tool/`][package-dir] for the reusable
   implementation.

## Safe vs. Writing Commands

Use read-only commands while getting oriented. They are enough to validate a
checkout, inspect Weblate status, and confirm output alignment.

Read-only report commands inspect state and write only report files in the
current checkout. They do not upload to Weblate and do not push Git commits
unless a workflow explicitly does so.

Writer commands rebuild translation output files and may commit/push when run by
the configured GitHub Actions workflow. Before changing a writer, read its
runbook and its tests.

The [Command Reference](command-reference.md) marks common external-repository
commands by safety level.

## Where Changes Usually Belong

Use this as the quick route, then read [Architecture](architecture.md) for the
full ownership map. If the change goes into support packages, use
[Internal Change Guide](internal-change-guide.md).

| Change | Start With | Tests |
| --- | --- | --- |
| Translation tree, final PO, or final KM output | [Architecture](architecture.md) | [`tests/translation/`][tests-translation] |
| Shared strings | [Architecture](architecture.md) | shared-string tests under [`tests/translation/`][tests-translation] |
| Weblate download, merge, or sync commits | [Architecture](architecture.md) | Localize and CI tests under [`tests/infra/`][tests-infra] |
| Translation repository config | [Architecture](architecture.md) | config tests under [`tests/infra/`][tests-infra] |
| KM Registry discovery or guarded KM updates | [Architecture](architecture.md) | KM tests under [`tests/infra/`][tests-infra] |
| GitHub workflow wiring | [Architecture](architecture.md) | workflow tests under [`tests/infra/`][tests-infra] |

If the right place is unclear, add or adjust a small test that describes the
behavior you expect. The module ownership usually becomes obvious from there.

[package-dir]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/src/dsw_km_translation_tool
[cli-dir]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/src/dsw_km_translation_tool/cli
[tests-infra]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/tests/infra
[tests-translation]: https://github.com/ThreeMonth03/dsw-km-translation-tool/tree/master/tests/translation
