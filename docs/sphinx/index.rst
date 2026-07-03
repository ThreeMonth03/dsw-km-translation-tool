DSW KM Translation Tooling
=======================================

This Sphinx site documents maintainer workflows and stable Python modules used
by the KM translation tooling and GitHub Actions workflows.

Start with the first-time maintainer guide when you are new to the codebase.
Use the package reference when checking maintainer-facing services, shared data
contracts, and report models. Use the internal change guide for implementation
helpers below those facades.

.. toctree::
   :maxdepth: 2
   :caption: Maintainer Docs

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

   api/translation-tree
   api/localize-sync
   api/reports-and-km
   api/data-models
