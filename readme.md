# DSW Translation Tool

Python tooling for DSW Knowledge Model translation maintenance.

For zh-Hant production work, the latest translation state is maintained in
Localize/Weblate. This repository provides automation and visualization around
that workflow:

- mirror Weblate PO exports into a Git translation tree
- rebuild final PO and KM bundles
- validate translation repository configuration
- report Weblate PO health and artifact alignment
- update to a newer published source KM after validation passes

## Documentation

The documentation workflow publishes the maintainer docs and API reference when
GitHub Pages is enabled for the repository.

Start here:

- [First-Time Maintainer Guide](docs/first-time-maintainer.md)
- [Documentation Index](docs/README.md)
- [Architecture](docs/architecture.md)
- [Development Guidelines](docs/development-guidelines.md)
- [Localize Sync Runbook](docs/localize-sync-runbook.md)
- [KM Update Runbook](docs/km-update-runbook.md)
- [Command Reference](docs/command-reference.md)

## Setup

```shell
make install-dev
```

This creates `.venv` and installs the Python dependencies listed in
`config/requirements.txt`.

## Common Commands

Run local checks before pushing tooling changes:

```shell
make check
```

Use `make help` for the common maintainer targets and `make help-all` for
lower-level repair helpers. The targets and Make variables are declared in the
[`Makefile`][makefile].

Read [Command Reference](docs/command-reference.md) before running targets that
rebuild translation artifacts or write Git commits. Configure workflow secrets
from [Security and Permissions](docs/security-and-permissions.md).

## Local Translation Tree Tools

Local tree commands are available for development, inspection, and repair. By
default they write to the ignored local workspace `translation/zh_Hant/`.
Production translation repositories use their own `translation-config.yml` and
repository layout; see [`examples/translation-config.yml`][example-translation-config].

[example-translation-config]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/examples/translation-config.yml
[makefile]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/Makefile
