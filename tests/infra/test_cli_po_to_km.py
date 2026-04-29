"""CLI integration tests for PO-to-KM conversion behavior."""

from __future__ import annotations

import json

from tests.helpers import parse_po_entries
from tests.infra.support import assert_cli_success, run_po_to_km_cli


def test_po_to_km_cli_generates_translated_km(
    repo_root,
    workflow,
    po_path,
    model_path,
    workspace,
) -> None:
    """Verify that the PO-to-KM CLI writes a translated KM bundle.

    Args:
        repo_root: Repository root fixture.
        workflow: Workflow service fixture.
        po_path: Fixture translated PO path.
        model_path: Fixture original KM path.
        workspace: Per-test temporary workspace fixture.
    """

    output_km = workspace / "cli-translated.km"
    normalize = workflow._normalize_expected_translation
    result = run_po_to_km_cli(
        repo_root=repo_root,
        translated_po_path=po_path,
        original_model_path=model_path,
        output_km_path=output_km,
    )

    assert_cli_success(result)
    assert "Generated KM file:" in result.stdout
    assert "as dsw:root-zh-hant:2.7.0" in result.stdout
    assert output_km.exists()

    bundle = json.loads(output_km.read_text(encoding="utf-8"))
    assert bundle["id"] == "dsw:root-zh-hant:2.7.0"
    assert bundle["kmId"] == "root-zh-hant"

    latest_by_uuid, _ = workflow.model_service.load_model(str(output_km))
    po_entries = parse_po_entries(po_path)
    filled_entries = [entry for entry in po_entries if entry.msgstr][:10]
    empty_entry = next(entry for entry in po_entries if not entry.msgstr)

    for entry in filled_entries:
        actual_text = workflow.model_service.get_event_text_value(
            latest_by_uuid.get(entry.uuid),
            entry.field,
        )
        assert actual_text == normalize(entry.msgstr)

    preserved_text = workflow.model_service.get_event_text_value(
        latest_by_uuid.get(empty_entry.uuid),
        empty_entry.field,
    )
    assert preserved_text == normalize(empty_entry.msgid)
