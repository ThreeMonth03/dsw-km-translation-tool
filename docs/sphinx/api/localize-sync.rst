Localize and Git Sync
=====================

Maintainer-facing config, pull, merge, tree refresh, and CI writer entrypoints
for Weblate-to-Git synchronization. Helper functions that implement one narrow
decision stay out of this reference; use the internal change guide and tests
when changing them.

Repository Configuration
------------------------

.. autoclass:: dsw_km_translation_tool.translation_repository_config.TranslationRepositoryConfigError

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

.. autofunction:: dsw_km_translation_tool.translation_repository_config.validate_supported_version

.. autofunction:: dsw_km_translation_tool.translation_repository_config.sorted_versions

.. autofunction:: dsw_km_translation_tool.translation_repository_config.format_package_id

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

PO Merge
--------

.. autoclass:: dsw_km_translation_tool.localize_merge.LocalizeMergeDecision
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.localize_merge.LocalizeMergeResult
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.localize_merge.PoEntryState
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.localize_merge.LocalizePoMerger
   :members:
   :show-inheritance:

CI Writer
---------

.. autofunction:: dsw_km_translation_tool.repository_ci_sync.build_repository_ci_sync_config

.. autoclass:: dsw_km_translation_tool.ci_sync.CiSyncError

.. autoclass:: dsw_km_translation_tool.ci_sync.CiSyncCommitConfig
   :members:
   :show-inheritance:

.. autofunction:: dsw_km_translation_tool.ci_sync.run_ci_sync_commit
