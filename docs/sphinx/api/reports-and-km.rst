Reports and KM Updates
======================

Maintainer-facing report models, renderers, and guarded KM update entrypoints.
Use runbooks for operational steps and the internal change guide for helper
implementation details.

Alignment Report
----------------

.. autoclass:: dsw_km_translation_tool.alignment_status.AlignmentArtifact
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.alignment_status.AlignmentCheck
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.alignment_status.AlignmentStatusReport
   :members:
   :show-inheritance:

.. autofunction:: dsw_km_translation_tool.alignment_status.build_alignment_status_report

.. autofunction:: dsw_km_translation_tool.alignment_status.render_alignment_status_markdown

.. autofunction:: dsw_km_translation_tool.alignment_status.write_alignment_status_json

.. autofunction:: dsw_km_translation_tool.alignment_status.write_alignment_status_markdown

Localize/Weblate Status
-----------------------

.. autoclass:: dsw_km_translation_tool.localize_status.LocalizePoReferenceStatus
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.localize_status.LocalizePoIssue
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.localize_status.LocalizePoStatusReport
   :members:
   :show-inheritance:

.. autofunction:: dsw_km_translation_tool.localize_status.build_localize_po_status_report

.. autofunction:: dsw_km_translation_tool.localize_status.render_localize_po_status_markdown

.. autofunction:: dsw_km_translation_tool.localize_status.write_localize_po_status_json

.. autofunction:: dsw_km_translation_tool.localize_status.write_localize_po_status_markdown

.. autoclass:: dsw_km_translation_tool.weblate_checks.WeblateCheckIssue
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.weblate_checks.WeblateChecksReport
   :members:
   :show-inheritance:

.. autofunction:: dsw_km_translation_tool.weblate_checks.build_weblate_checks_report

.. autofunction:: dsw_km_translation_tool.weblate_checks.build_weblate_checks_error_report

.. autofunction:: dsw_km_translation_tool.weblate_checks.resolve_weblate_units_api_url

.. autofunction:: dsw_km_translation_tool.weblate_checks.render_weblate_checks_markdown

.. autofunction:: dsw_km_translation_tool.weblate_checks.write_weblate_checks_json

.. autofunction:: dsw_km_translation_tool.weblate_checks.write_weblate_checks_markdown

KM Registry and Bundle Sync
---------------------------

.. autoclass:: dsw_km_translation_tool.km_registry.KmRegistryError

.. autoclass:: dsw_km_translation_tool.km_registry.KmRegistryPackage
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.km_registry.KmVersionDiscoveryResult
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.km_registry.KmRegistryClient
   :members:
   :show-inheritance:

.. autofunction:: dsw_km_translation_tool.km_registry.discover_km_versions

.. autofunction:: dsw_km_translation_tool.km_registry.discover_km_versions_for_config

.. autofunction:: dsw_km_translation_tool.km_registry.render_km_version_discovery_markdown

.. autofunction:: dsw_km_translation_tool.km_registry.write_km_version_discovery_report

.. autofunction:: dsw_km_translation_tool.km_registry.write_km_version_discovery_markdown

.. autoclass:: dsw_km_translation_tool.km_bundle_sync.KmBundlePullResult
   :members:
   :show-inheritance:

.. autofunction:: dsw_km_translation_tool.km_bundle_sync.pull_km_bundle

.. autoclass:: dsw_km_translation_tool.km_latest_sync.KmLatestSyncError

.. autoclass:: dsw_km_translation_tool.km_latest_sync.KmLatestSyncResult
   :members:
   :show-inheritance:

.. autofunction:: dsw_km_translation_tool.km_latest_sync.sync_latest_km_version

.. autofunction:: dsw_km_translation_tool.km_latest_sync.update_supported_versions_in_config

.. autofunction:: dsw_km_translation_tool.km_latest_sync.render_km_latest_sync_markdown

.. autofunction:: dsw_km_translation_tool.km_latest_sync.write_km_latest_sync_report

.. autofunction:: dsw_km_translation_tool.km_latest_sync.write_km_latest_sync_markdown
