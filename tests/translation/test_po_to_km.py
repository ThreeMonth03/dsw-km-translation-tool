"""Tests for direct PO -> KM bundle conversion."""

from __future__ import annotations

import json
from pathlib import Path

from dsw_translation_tool.data_models import PoBlock
from dsw_translation_tool.po import PoCatalogParser, PoStringCodec
from tests.helpers import parse_po_entries


def test_build_km_from_po_applies_translated_msgstrs_to_latest_model_fields(
    workflow,
    po_path,
    model_path,
    workspace,
) -> None:
    """Verify that PO translations are applied to the final KM state.

    Args:
        workflow: Workflow service fixture.
        po_path: Fixture translated PO path.
        model_path: Fixture original KM path.
        workspace: Per-test temporary workspace fixture.
    """

    output_km = workspace / "translated-from-po.km"
    po_entries = parse_po_entries(po_path)
    normalize = workflow._normalize_expected_translation

    result = workflow.build_km_from_po(
        translated_po_path=str(po_path),
        original_model_path=str(model_path),
        out_model_path=str(output_km),
    )

    assert result.output_km == output_km
    assert result.total_entries == len(po_entries)
    assert result.translated_entries == sum(1 for entry in po_entries if entry.msgstr)
    assert result.preserved_entries == sum(1 for entry in po_entries if not entry.msgstr)
    assert result.output_package_id == "dsw:root-zh-hant:2.7.0"
    assert result.output_km_id == "root-zh-hant"
    assert result.output_name == "Common DSW Knowledge Model (zh_Hant)"
    assert output_km.exists()

    bundle = json.loads(output_km.read_text(encoding="utf-8"))
    assert bundle["id"] == "dsw:root-zh-hant:2.7.0"
    assert bundle["organizationId"] == "dsw"
    assert bundle["kmId"] == "root-zh-hant"
    assert bundle["name"] == "Common DSW Knowledge Model (zh_Hant)"
    assert "dsw:root:" not in output_km.read_text(encoding="utf-8")
    for package in bundle["packages"]:
        expected_package_id = f"dsw:root-zh-hant:{package['version']}"
        assert package["id"] == expected_package_id
        assert package["organizationId"] == "dsw"
        assert package["kmId"] == "root-zh-hant"
        if package["previousPackageId"]:
            assert package["previousPackageId"].startswith("dsw:root-zh-hant:")

    latest_by_uuid, _ = workflow.model_service.load_model(str(output_km))
    for entry in po_entries:
        expected_text = normalize(entry.msgstr or entry.msgid)
        actual_text = workflow.model_service.get_event_text_value(
            latest_by_uuid.get(entry.uuid),
            entry.field,
        )
        assert actual_text == expected_text


def test_fully_translated_shared_msgid_roundtrips_from_km_to_translation_tree(
    workflow,
    po_path,
    model_path,
    workspace,
) -> None:
    """Verify that every reference in a translated shared PO block reaches the tree.

    Args:
        workflow: Workflow service fixture.
        po_path: Fixture translated PO path.
        model_path: Fixture original KM path.
        workspace: Per-test temporary workspace fixture.
    """

    shared_block = select_shared_msgid_block(po_path)
    translated_text = "完整翻譯：共享 msgid 應該套用到每一個 reference"
    translated_po = workspace / "one-shared-msgid-translated.po"
    generated_km = workspace / "one-shared-msgid-translated.km"
    roundtrip_po = workspace / "one-shared-msgid-roundtrip.po"
    roundtrip_tree = workspace / "one-shared-msgid-tree"

    write_single_block_po(
        path=translated_po,
        block=shared_block,
        msgid=shared_block.msgid,
        msgstr=translated_text,
    )

    workflow.build_km_from_po(
        translated_po_path=str(translated_po),
        original_model_path=str(model_path),
        out_model_path=str(generated_km),
    )

    latest_by_uuid, _ = workflow.model_service.load_model(str(generated_km))
    for reference in shared_block.references:
        actual_text = workflow.model_service.get_event_text_value(
            latest_by_uuid.get(reference.uuid),
            reference.field,
        )
        assert actual_text == translated_text

    write_single_block_po(
        path=roundtrip_po,
        block=shared_block,
        msgid=translated_text,
        msgstr=translated_text,
    )
    context = workflow.export_tree(
        po_path=str(roundtrip_po),
        model_path=str(generated_km),
        out_dir=str(roundtrip_tree),
        preserve_existing_translations=False,
    )

    assert context.report["missingEntities"] == 0
    assert context.report["missingFields"] == 0
    assert context.report["mismatches"] == 0

    scan_result = workflow.tree_repository.scan(str(roundtrip_tree))
    for reference in shared_block.references:
        state = scan_result.folders_by_uuid[reference.uuid].fields[reference.field]
        assert state.source_text == translated_text
        assert state.target_text == translated_text


def select_shared_msgid_block(po_path: Path) -> PoBlock:
    """Select one PO block that maps the same msgid to multiple KM fields.

    Args:
        po_path: Source PO path to scan.

    Returns:
        First multi-reference PO block.

    Raises:
        AssertionError: If no shared-msgid block exists in the fixture.
    """

    for block in PoCatalogParser(str(po_path)).parse_blocks():
        if len(block.references) >= 2:
            return block
    raise AssertionError("Expected at least one shared msgid block with multiple references")


def write_single_block_po(
    path: Path,
    block: PoBlock,
    msgid: str,
    msgstr: str,
) -> None:
    """Write a minimal PO file containing one selected reference block.

    Args:
        path: Destination PO path.
        block: PO block whose references should be preserved.
        msgid: Source text to serialize.
        msgstr: Target text to serialize.
    """

    comments = " ".join(reference.comment for reference in block.references)
    path.write_text(
        "\n".join(
            (
                f"#: {comments}",
                f'msgid "{PoStringCodec.escape(msgid)}"',
                f'msgstr "{PoStringCodec.escape(msgstr)}"',
                "",
            )
        ),
        encoding="utf-8",
    )
