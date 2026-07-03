# Documentation Index

Use this directory as the maintenance manual for the DSW translation tooling.
The root [`readme.md`][root-readme] stays as the translator-friendly entry point and quick
command reference; durable design and operating procedures live here.

## If You Need to...

| Task | Read |
| --- | --- |
| Get oriented before changing code | [First-Time Maintainer Guide](first-time-maintainer.md) |
| Understand which module owns a behavior | [Architecture](architecture.md) |
| Change code safely | [Development Guidelines](development-guidelines.md) |
| Operate Localize/Weblate-to-Git sync | [Localize Sync Runbook](localize-sync-runbook.md) |
| Check repository/Weblate build alignment | [Localize Sync Runbook](localize-sync-runbook.md) |
| Configure workflow permissions and secrets | [Security and Permissions](security-and-permissions.md) |
| Move the tooling repository to another GitHub owner | [Repository Transfer Checklist](repository-transfer-checklist.md) |
| Monitor, automatically update, or manually repair a future KM version update | [KM Update Runbook](km-update-runbook.md) |
| Find a Make target or CLI command | [Command Reference](command-reference.md) |
| Browse developer API docs | `make docs`, then open `docs/sphinx/_build/html/index.html` |

## Documentation Ownership

- Use [First-Time Maintainer Guide](first-time-maintainer.md) as the newcomer
  route into the codebase.
- Use [Architecture](architecture.md) for module ownership.
- Use runbooks for operating production workflows.
- Use [Security and Permissions](security-and-permissions.md) for secrets and
  workflow permissions.
- Use [Command Reference](command-reference.md) for command syntax and safety.
- Use Sphinx API pages for stable package modules and docstrings.

[root-readme]: https://github.com/ThreeMonth03/DSW_Translation_tool/blob/master/readme.md
