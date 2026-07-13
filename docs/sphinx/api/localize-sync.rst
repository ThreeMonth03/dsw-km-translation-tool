Localize and Git Sync
=====================

Use this page for maintainer-facing config, pull, tree refresh, and CI
writer entrypoints in Weblate-to-Git synchronization. It is the code companion
to the Localize sync runbook. Use the internal change guide for narrow helper
behavior behind these entrypoints.

Repository Configuration
------------------------

.. py:exception:: dsw_km_translation_tool.translation_repository_config.TranslationRepositoryConfigError

   Raised when a translation repository config is invalid.

.. autoclass:: dsw_km_translation_tool.translation_repository_config.KnowledgeModelRepositoryConfig
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.translation_repository_config.TranslationLanguageConfig
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.translation_repository_config.BranchConfig
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.translation_repository_config.ToolingConfig
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.translation_repository_config.LocalizeConfig
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.translation_repository_config.RegistryConfig
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.translation_repository_config.KmVersionWorkspacePaths
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.translation_repository_config.TranslationRepositoryConfig
   :members:
   :show-inheritance:

.. autofunction:: dsw_km_translation_tool.translation_repository_config.load_translation_repository_config

.. autofunction:: dsw_km_translation_tool.translation_repository_config.tracking_branch

.. autofunction:: dsw_km_translation_tool.translation_repository_config.version_paths

.. autofunction:: dsw_km_translation_tool.translation_repository_config.format_package_id

Translation Repository Bootstrap
--------------------------------

.. py:exception:: dsw_km_translation_tool.translation_repository_bootstrap.TranslationRepositoryBootstrapError

   Raised when a translation repository cannot be bootstrapped.

.. autoclass:: dsw_km_translation_tool.translation_repository_bootstrap.TranslationRepositoryBootstrapResult
   :members:
   :show-inheritance:

.. autofunction:: dsw_km_translation_tool.translation_repository_bootstrap.bootstrap_translation_repository

Translation Repository Scaffold
-------------------------------

.. py:exception:: dsw_km_translation_tool.translation_repository_scaffold.TranslationRepositoryScaffoldError

   Raised when managed repository files cannot be rendered.

.. autoclass:: dsw_km_translation_tool.translation_repository_scaffold.TranslationRepositoryScaffoldResult
   :members:
   :show-inheritance:

.. autofunction:: dsw_km_translation_tool.translation_repository_scaffold.check_translation_repository_scaffold

.. autofunction:: dsw_km_translation_tool.translation_repository_scaffold.sync_translation_repository_scaffold

Localize Pull and Tree Refresh
------------------------------

.. autoclass:: dsw_km_translation_tool.localize_sync.LocalizePullResult
   :members:
   :show-inheritance:

.. autofunction:: dsw_km_translation_tool.localize_sync.pull_localize_po

.. autoclass:: dsw_km_translation_tool.localize_tree_sync.LocalizeTreeRefreshResult
   :members:
   :show-inheritance:

.. autofunction:: dsw_km_translation_tool.localize_tree_sync.refresh_tree_from_localize

CI Writer
---------

.. autofunction:: dsw_km_translation_tool.repository_ci_sync.build_repository_ci_sync_config

.. py:exception:: dsw_km_translation_tool.ci_sync.CiSyncError

   Raised when CI sync-and-commit automation cannot complete.

.. autoclass:: dsw_km_translation_tool.ci_sync.CiSyncCommitConfig
   :members:
   :show-inheritance:

.. autofunction:: dsw_km_translation_tool.ci_sync.run_ci_sync_commit

GitHub Translation Contributions
--------------------------------

.. py:exception:: dsw_km_translation_tool.github_translation_contributions.GitHubTranslationContributionError

   Raised when GitHub translation contribution analysis cannot complete.

.. autoclass:: dsw_km_translation_tool.github_translation_contributions.TreeTranslationEntry
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.github_translation_contributions.GitHubTranslationDecision
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.github_translation_contributions.GitHubTranslationReport
   :members:
   :show-inheritance:

.. autofunction:: dsw_km_translation_tool.github_translation_contributions.build_github_translation_report

.. autofunction:: dsw_km_translation_tool.github_translation_contributions.render_github_translation_markdown

.. autofunction:: dsw_km_translation_tool.github_translation_contributions.write_github_translation_json

.. autofunction:: dsw_km_translation_tool.github_translation_contributions.write_github_translation_markdown

.. autofunction:: dsw_km_translation_tool.github_translation_contributions.write_import_po

.. autoclass:: dsw_km_translation_tool.weblate_upload.WeblateUploadResult
   :members:
   :show-inheritance:

.. autofunction:: dsw_km_translation_tool.weblate_upload.resolve_weblate_file_api_url

.. autofunction:: dsw_km_translation_tool.weblate_upload.upload_translation_file
