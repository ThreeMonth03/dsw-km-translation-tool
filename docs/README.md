# Documentation Index

Use this directory as the maintenance manual for the DSW translation tooling.
The root `readme.md` stays as the translator-friendly entry point and quick
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

## Maintenance Notes

- Keep Localize/Weblate as the latest translation authority for zh-Hant
  production work.
- Keep workflow YAML thin. Put parsing, merge, Git, and Weblate decisions in
  Python helpers with tests.
- Keep root CLI scripts in `src/*.py` as small entry points; reusable behavior
  belongs in `src/dsw_translation_tool/`.
- Give new maintainers a task-oriented path before sending them into the API
  reference.
- Document both the command and the failure mode when adding an automation
  helper.
- Keep repository-owner moves explicit. Update tooling checkout references,
  workflow templates, tests, and GitHub settings together.
- Keep Sphinx pages focused on stable package modules. Put operational
  procedures in the Markdown runbooks.
