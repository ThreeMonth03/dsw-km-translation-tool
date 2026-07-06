DSW KM Translation Tooling
=======================================

This site documents the tooling used to keep DSW Knowledge Model translations
aligned between Weblate, a Git translation repository, and validated KM outputs.

The latest translation text is edited in Weblate. This repository provides the
automation around that workflow: sync, reports, validation, and guarded KM
updates.

Start Here
----------

Choose the path closest to what you are doing:

- **New to the repository**: read the
  :doc:`First-Time Maintainer Guide <maintainer/first-time-maintainer>` first.
  It explains the mental model, safe commands, and where common changes belong.

- **Operating production sync**: use the
  :doc:`Localize Sync Runbook <maintainer/localize-sync-runbook>` for
  Weblate-to-Git sync, status reports, and alignment checks.

- **Creating a translation repository**: use
  :doc:`Translation Repository Bootstrap <maintainer/translation-repository-bootstrap>`
  to scaffold workflows/docs/config and hydrate upstream KM/PO inputs.

- **Updating to a newer KM**: use the
  :doc:`KM Update Runbook <maintainer/km-update-runbook>` for the guarded
  auto-update workflow and manual repair path.

- **Changing the tooling**: start with
  :doc:`Architecture <maintainer/architecture>`, then use the
  :doc:`Internal Change Guide <maintainer/internal-change-guide>` when editing
  lower-level helpers.

- **Finding commands**: use the
  :doc:`Command Reference <maintainer/command-reference>` for Make targets,
  required variables, and writer commands.

Package Reference
-----------------

Use these pages when you need maintainer-facing Python interfaces, shared data
contracts, or report models:

- :doc:`Translation Tree Reference <api/translation-tree>`
- :doc:`Localize and Git Sync <api/localize-sync>`
- :doc:`Reports and KM Updates <api/reports-and-km>`
- :doc:`Data Models <api/data-models>`

For implementation helpers below these facades, use the
:doc:`Internal Change Guide <maintainer/internal-change-guide>`.

.. toctree::
   :maxdepth: 2
   :caption: Maintainer Docs
   :hidden:

   maintainer/first-time-maintainer
   maintainer/architecture
   maintainer/development-guidelines
   maintainer/command-reference
   maintainer/localize-sync-runbook
   maintainer/km-update-runbook
   maintainer/translation-repository-bootstrap
   maintainer/workflow-templates
   maintainer/security-and-permissions
   maintainer/internal-change-guide
   maintainer/repository-transfer-checklist

.. toctree::
   :maxdepth: 2
   :caption: Package Reference
   :hidden:

   api/translation-tree
   api/localize-sync
   api/reports-and-km
   api/data-models
