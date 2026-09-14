"""Native locale releases are reproducible and independent of source releases."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from dsw_km_translation_tool.locale_release import (
    LocaleReleaseError,
    locale_revision,
    prepare_locale_release,
)
from dsw_km_translation_tool.po_support.state import parse_po_entry_states
from dsw_km_translation_tool.shared_blocks.parser import SharedBlocksCatalogParser
from dsw_km_translation_tool.translation_repository_build import build_translation_repository
from dsw_km_translation_tool.translation_repository_config import (
    load_translation_repository_config,
    version_paths,
)
from tests.helpers import update_shared_block_translation
from tests.infra.test_translation_repository_config import write_config


@pytest.mark.parametrize("revision", [1, 2, 15])
def test_locale_revision_is_independent_of_km_version(revision: int) -> None:
    assert locale_revision(f"km-2.7.0-zh_Hant-r{revision}", "2.7.0", "zh_Hant") == revision


@pytest.mark.parametrize(
    "tag", ["v2.7.0", "km-2.7.0-de-r1", "km-2.7.1-zh_Hant-r1", "km-2.7.0-zh_Hant-r0"]
)
def test_locale_revision_rejects_mismatched_tags(tag: str) -> None:
    with pytest.raises(LocaleReleaseError, match="Expected release tag"):
        locale_revision(tag, "2.7.0", "zh_Hant")


@pytest.fixture
def release_repositories(workspace: Path, model_path: Path, po_path: Path) -> tuple[Path, Path]:
    tool = workspace / "tool"
    tool.mkdir()
    (tool / "README.md").write_text("Pinned tooling\n", encoding="utf-8")
    tool_sha = _commit(tool)
    root = workspace / "translation"
    root.mkdir()
    config_file = root / "translation-config.yml"
    write_config(config_file)
    config_file.write_text(config_file.read_text().replace("ref: master", f"ref: {tool_sha}"))
    paths = version_paths(load_translation_repository_config(config_file))
    for source, target in ((model_path, paths.source_km_path), (po_path, paths.source_po_path)):
        (root / target).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, root / target)
    build_translation_repository(repo_root=root)
    _commit(root)
    return root, tool


def test_locale_release_rebuilds_and_records_verified_assets(
    release_repositories: tuple[Path, Path],
    workspace: Path,
) -> None:
    root, tool = release_repositories
    output = workspace / "assets"
    manifest = prepare_locale_release(
        repo_root=root,
        tooling_repo=tool,
        tag="km-2.7.0-zh_Hant-r2",
        output_dir=output,
    )
    assert manifest["revision"] == 2
    assert manifest["knowledge_model"]["package_id"] == "dsw:root:2.7.0"
    assert manifest["po"]["messages"] == 1466
    assets = output / "assets"
    assert json.loads((assets / "manifest.json").read_text()) == manifest
    name = "dsw-root-zh_Hant-locale-2.7.0-r2.po"
    assert {p.name for p in assets.iterdir()} == {name, "manifest.json", "SHA256SUMS"}
    assert {p.name for p in output.iterdir()} == {"assets", "release-notes.md"}
    assert (assets / name).read_bytes() == (root / "builds/final_translated.po").read_bytes()
    checksum_lines = (assets / "SHA256SUMS").read_text().splitlines()
    assert {line.split("  ")[1] for line in checksum_lines} == {name, "manifest.json"}
    for line in checksum_lines:
        checksum, filename = line.split("  ")
        assert hashlib.sha256((assets / filename).read_bytes()).hexdigest() == checksum
    with pytest.raises(LocaleReleaseError, match="already exists"):
        prepare_locale_release(
            repo_root=root,
            tooling_repo=tool,
            tag="km-2.7.0-zh_Hant-r2",
            output_dir=output,
        )


def test_build_preserves_canonical_only_edits_but_release_requires_committed_outputs(
    release_repositories: tuple[Path, Path],
    workspace: Path,
) -> None:
    root, tool = release_repositories
    shared_dir = root / "tree/shared_blocks"
    groups = SharedBlocksCatalogParser().parse(str(shared_dir))
    key = next(iter(groups))
    target = "測試共用翻譯"
    update_shared_block_translation(
        shared_blocks_root=shared_dir, group_key=key, target_text=target
    )
    _commit(root)
    with pytest.raises(LocaleReleaseError, match="verify release checkout"):
        prepare_locale_release(
            repo_root=root,
            tooling_repo=tool,
            tag="km-2.7.0-zh_Hant-r1",
            output_dir=workspace / "assets",
        )
    states = parse_po_entry_states(root / "builds/final_translated.po")
    assert all(states[item].msgstr == target for item in key)


@pytest.mark.parametrize("ref", ["master", "1" * 40])
def test_locale_release_rejects_unpinned_or_mismatched_tooling(
    release_repositories: tuple[Path, Path],
    workspace: Path,
    ref: str,
) -> None:
    root, tool = release_repositories
    config_file = root / "translation-config.yml"
    config = load_translation_repository_config(config_file)
    config_file.write_text(config_file.read_text().replace(config.tooling.ref, f'"{ref}"'))
    _commit(root)
    with pytest.raises(LocaleReleaseError, match="full commit SHA|does not match tooling.ref"):
        prepare_locale_release(
            repo_root=root,
            tooling_repo=tool,
            tag="km-2.7.0-zh_Hant-r1",
            output_dir=workspace / "assets",
        )


def _commit(root: Path) -> str:
    commands = [
        ["init", "-q"],
        ["config", "user.name", "Test"],
        ["config", "user.email", "test@example.com"],
        ["add", "."],
        ["commit", "-qm", "Fixture"],
        ["rev-parse", "HEAD"],
    ]
    for args in commands:
        result = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, check=True
        )
    return result.stdout.strip()
