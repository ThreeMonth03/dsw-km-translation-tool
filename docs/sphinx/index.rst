DSW KM Translation Tooling
=======================================

This site documents the tooling used to keep DSW Knowledge Model translations
aligned between Weblate, a Git translation repository, and validated KM outputs.

The latest translation text is edited in Weblate. This repository provides the
automation around that workflow: sync, reports, validation, and guarded KM
updates.

Start Here
----------

New to the repository
   Read the :doc:`First-Time Maintainer Guide <maintainer/first-time-maintainer>`
   first. It explains the mental model, safe commands, and where common changes
   belong.

Operating production sync
   Use the :doc:`Localize Sync Runbook <maintainer/localize-sync-runbook>` for
   Weblate-to-Git sync, status reports, and alignment checks.

Updating to a newer KM
   Use the :doc:`KM Update Runbook <maintainer/km-update-runbook>` for the
   guarded auto-update workflow and manual repair path.

Changing the tooling
   Start with :doc:`Architecture <maintainer/architecture>` and then use the
   :doc:`Internal Change Guide <maintainer/internal-change-guide>` when editing
   lower-level helpers.

Finding commands
   Use the :doc:`Command Reference <maintainer/command-reference>` for Make
   targets, required variables, and writer commands.

Reference Material
------------------

The package reference is intentionally selective. It documents maintainer-facing
services, shared data contracts, and report models. For implementation helpers
below those facades, use the internal change guide.

.. toctree::
   :maxdepth: 2
   :caption: Maintainer Docs
   :hidden:

   maintainer/first-time-maintainer
   maintainer/docs-index
   maintainer/architecture
   maintainer/internal-change-guide
   maintainer/command-reference
   maintainer/development-guidelines
   maintainer/workflow-templates
   maintainer/localize-sync-runbook
   maintainer/km-update-runbook
   maintainer/repository-transfer-checklist
   maintainer/security-and-permissions

.. toctree::
   :maxdepth: 2
   :caption: Package Reference
   :hidden:

   api/translation-tree
   api/localize-sync
   api/reports-and-km
   api/data-models
