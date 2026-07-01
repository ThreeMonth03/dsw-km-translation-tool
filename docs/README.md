# Documentation Index

Use this directory as the maintenance manual for the DSW translation tooling.
The root `readme.md` stays as the translator-friendly entry point and quick
command reference; durable design and operating procedures live here.

## If You Need to...

| Task | Read |
| --- | --- |
| Understand which module owns a behavior | [Architecture](architecture.md) |
| Change code safely | [Development Guidelines](development-guidelines.md) |
| Operate Localize/Weblate-to-Git sync | [Localize Sync Runbook](localize-sync-runbook.md) |
| Check repository/Weblate build alignment | [Localize Sync Runbook](localize-sync-runbook.md) |
| Configure workflow permissions and secrets | [Security and Permissions](security-and-permissions.md) |
| Prepare a future KM version update | [KM Update Runbook](km-update-runbook.md) |
| Find a Make target or CLI command | [Command Reference](command-reference.md) |
| Prepare a one-shot repository-to-Weblate migration | [Localize Sync Runbook](localize-sync-runbook.md) and [Command Reference](command-reference.md) |

## Maintenance Rules

- Keep Localize/Weblate as the latest translation authority for zh-Hant
  production work.
- Keep workflow YAML thin. Put parsing, merge, Git, and Weblate decisions in
  Python helpers with tests.
- Keep root CLI scripts in `src/*.py` as small entry points; reusable behavior
  belongs in `src/dsw_translation_tool/`.
- Document both the command and the failure mode when adding an automation
  helper.
- Do not add scheduled Git-to-Weblate uploads. Repository-to-Weblate upload is
  an explicit migration or repair operation only.
- Do not rewrite public `master` history to clean up intermediate automation
  commits. Use forward fixes unless maintainers explicitly coordinate a history
  rewrite.
