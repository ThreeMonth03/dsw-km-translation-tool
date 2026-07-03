Translation Tree Reference
==========================

Use this page for maintainer-facing services in local PO, KM, translation tree,
review, and shared-string workflows. Use the internal change guide for parser,
renderer, storage, and other support-module implementation details.

Workflow Service
----------------

Only the primary workflow operations are listed here. Thinner helper methods
exist for CLI wiring and tests; use the internal change guide before changing
those lower-level paths.

.. autoclass:: dsw_km_translation_tool.workflow.TranslationWorkflowService
   :members: export_tree, validate_po_against_model, build_po_from_tree, build_km_from_po, collect_status, sync_shared_strings, review_po_changes
   :show-inheritance:

Tree Repository
---------------

.. autoclass:: dsw_km_translation_tool.tree.TranslationTreeRepository
   :members:
   :exclude-members: __init__
   :show-inheritance:

Knowledge Model Service
-----------------------

This service keeps DSW KM parsing and validation behind one boundary. The
tree-building and display-name internals are implementation details covered by
the internal change guide.

.. autoclass:: dsw_km_translation_tool.knowledge_model_service.KnowledgeModelService
   :members: load_model, annotate_tree_nodes, validate_po_entries
   :show-inheritance:

PO Facade
---------

The PO facade exports the parser, writer, and string codec used by workflow
services. Their parser/render internals are intentionally not expanded here;
use the internal change guide before changing PO support behavior.

.. autoclass:: dsw_km_translation_tool.po.PoCatalogParser
   :members: parse_blocks, parse_entries
   :exclude-members: __init__, __new__
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.po.PoCatalogWriter
   :members: rewrite_translations
   :exclude-members: __init__, __new__
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.po.PoStringCodec
   :members: decode, escape
   :exclude-members: __new__, __init__
   :show-inheritance:

Review and Shared Strings
-------------------------

.. autoclass:: dsw_km_translation_tool.review.PoDiffReviewer
   :members:
   :exclude-members: __init__
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.shared_blocks.SharedBlockContext
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.shared_blocks.SharedBlockRecord
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.shared_blocks.SharedBlocksCatalogParser
   :members:
   :exclude-members: __init__
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.shared_blocks.SharedBlocksCatalogBuilder
   :members:
   :exclude-members: __init__
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.sync.SharedStringSynchronizer
   :members:
   :exclude-members: __init__
   :show-inheritance:
