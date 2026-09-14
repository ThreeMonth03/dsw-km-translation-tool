"""Source refreshes must not discard translations awaiting Weblate import."""

from __future__ import annotations

import shutil

import pytest

from dsw_km_translation_tool.km_latest_sync import sync_latest_km_version
from dsw_km_translation_tool.localize_sync import pull_localize_po
from dsw_km_translation_tool.translation_repository_build import build_translation_repository
from tests.infra.test_km_latest_sync import RecordingRunner, candidate_bundle, registry_payload
from tests.infra.test_translation_repository_config import write_config


@pytest.fixture
def pending_repository(workspace, model_path):
    config = workspace / "translation-config.yml"
    write_config(config)
    km = workspace / "sources/knowledge-models/dsw-root-2.7.0/dsw-root-2.7.0.km"
    km.parent.mkdir(parents=True)
    shutil.copyfile(model_path, km)
    payload = (
        'msgid ""\nmsgstr ""\n"Language: zh_Hant\\n"\n'
        "\n#: phase/ffffffff-ffff-4fff-8fff-ffffffffffff/title\n"
        'msgid "Single title"\nmsgstr "原譯"\n'
        "\n#: phase/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/title "
        "phase/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb/title\n"
        'msgid "Shared title"\nmsgstr "共用原譯"\n'
    ).encode()
    pull_localize_po(config_path=config, repo_root=workspace, downloader=lambda _: payload)
    build_translation_repository(repo_root=workspace, preserve_existing_translations=False)
    return workspace, config, payload


@pytest.mark.parametrize("shared", [False, True])
@pytest.mark.parametrize("target", ["待匯入譯文", ""])
def test_refresh_preserves_unimported_edits(pending_repository, shared, target):
    root, config, payload = pending_repository
    path, original = editable_path(root, shared)
    path.write_text(path.read_text().replace(original, target))
    before = repository_bytes(root)
    with pytest.raises(ValueError, match="not yet in Weblate"):
        pull_localize_po(config_path=config, repo_root=root, downloader=lambda _: payload)
    assert repository_bytes(root) == before


def editable_path(root, shared=False):
    if shared:
        return next((root / "tree/shared_blocks").glob("*/context.md")), "共用原譯"
    return (
        next(
            path
            for path in (root / "tree").rglob("translation.md")
            if "Single title" in path.read_text()
        ),
        "原譯",
    )


def repository_bytes(root):
    return {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}


@pytest.mark.parametrize("shared", [False, True])
@pytest.mark.parametrize("target", ["已匯入譯文", ""])
def test_refresh_resumes_after_verified_import(pending_repository, shared, target):
    root, config, payload = pending_repository
    path, original = editable_path(root, shared)
    path.write_text(path.read_text().replace(original, target))
    incoming = payload.replace(f'msgstr "{original}"'.encode(), f'msgstr "{target}"'.encode())
    pull_localize_po(config_path=config, repo_root=root, downloader=lambda _: incoming)
    result = build_translation_repository(repo_root=root, preserve_existing_translations=False)
    assert result.final_po_path.read_bytes() == incoming


def test_refresh_accepts_official_removals_and_fuzzy_without_local_edits(pending_repository):
    root, config, payload = pending_repository
    incoming = payload.split(b"\n#: phase/aaaaaaaa")[0].replace(
        'msgid "Single title"\nmsgstr "原譯"'.encode(),
        '#, fuzzy\nmsgid "Changed official title"\nmsgstr "官方草稿"'.encode(),
    )
    pull_localize_po(config_path=config, repo_root=root, downloader=lambda _: incoming)
    result = build_translation_repository(repo_root=root, preserve_existing_translations=False)
    assert result.final_po_path.read_bytes() == incoming


@pytest.mark.parametrize("removed", [False, True])
def test_refresh_does_not_replace_pending_edit_with_upstream_change(pending_repository, removed):
    root, config, payload = pending_repository
    path, original = editable_path(root)
    path.write_text(path.read_text().replace(original, "待匯入譯文"))
    incoming = payload.replace('msgstr "原譯"'.encode(), 'msgstr "Weblate另一個譯文"'.encode())
    if removed:
        start = incoming.index(b"\n#: phase/ffffffff")
        end = incoming.index(b"\n#: phase/aaaaaaaa")
        incoming = incoming[:start] + incoming[end:]
    before = repository_bytes(root)
    with pytest.raises(ValueError, match="not yet in Weblate"):
        pull_localize_po(config_path=config, repo_root=root, downloader=lambda _: incoming)
    assert repository_bytes(root) == before


def test_km_update_preserves_pending_edit_and_all_sources(pending_repository, model_path):
    root, config, payload = pending_repository
    path, original = editable_path(root, shared=True)
    path.write_text(path.read_text().replace(original, "待匯入譯文"))
    before = repository_bytes(root)
    runner = RecordingRunner()
    with pytest.raises(ValueError, match="not yet in Weblate"):
        sync_latest_km_version(
            repo_root=root,
            tooling_repo=root,
            config_path=config,
            registry_token="test-token",
            downloader=lambda _: registry_payload("2.7.0", "2.8.0"),
            bundle_downloader=lambda *_: candidate_bundle(model_path, "2.8.0"),
            localize_downloader=lambda _: payload,
            runner=runner,
        )
    assert repository_bytes(root) == before
    assert runner.command_names == ["git status --porcelain"]


@pytest.mark.parametrize("shared", [False, True])
def test_invalid_input_is_not_restored_or_overwritten(pending_repository, shared):
    root, config, payload = pending_repository
    path, _ = editable_path(root, shared)
    path.write_text(path.read_text().replace("~~~text", "broken fence", 1))
    before = repository_bytes(root)
    with pytest.raises(ValueError):
        pull_localize_po(config_path=config, repo_root=root, downloader=lambda _: payload)
    assert repository_bytes(root) == before
