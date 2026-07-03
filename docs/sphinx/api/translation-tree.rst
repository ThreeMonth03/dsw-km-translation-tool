Translation Tree Reference
==========================

Maintainer-facing services for local PO, KM, translation tree, review, and
shared-string workflows. This is not a public SDK; internal parser, renderer,
and storage helpers are covered by the internal change guide and tests.

Workflow Service
----------------

.. autoclass:: dsw_km_translation_tool.workflow.TranslationWorkflowService
   :members:
   :show-inheritance:

Tree Repository
---------------

.. autoclass:: dsw_km_translation_tool.tree.TranslationTreeRepository
   :members:
   :show-inheritance:

Knowledge Model Service
-----------------------

.. autoclass:: dsw_km_translation_tool.knowledge_model_service.KnowledgeModelService
   :members:
   :show-inheritance:

PO Facade
---------

The PO facade exports the parser, writer, and string codec used by workflow
services. Their parser/render internals are intentionally not expanded here;
use the internal change guide before changing PO support behavior.

.. autoclass:: dsw_km_translation_tool.po.PoCatalogParser

.. autoclass:: dsw_km_translation_tool.po.PoCatalogWriter

.. autoclass:: dsw_km_translation_tool.po.PoStringCodec

Review and Shared Strings
-------------------------

.. autoclass:: dsw_km_translation_tool.review.PoDiffReviewer
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.shared_blocks.SharedBlockContext
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.shared_blocks.SharedBlockRecord
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.shared_blocks.SharedBlocksCatalogParser
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.shared_blocks.SharedBlocksCatalogBuilder
   :members:
   :show-inheritance:

.. autoclass:: dsw_km_translation_tool.sync.SharedStringSynchronizer
   :members:
   :show-inheritance:
