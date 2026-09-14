"""Release planning ignores incidental PO changes and never reuses a tag."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from dsw_km_translation_tool.locale_release_plan import effective_translations, plan_locale_release
from tests.infra.test_github_translation_contributions import write_latest_po
from tests.infra.test_locale_release import _commit
from tests.infra.test_translation_repository_config import write_config


def _catalog(root: Path, translation: str) -> Path:
    path = root / "builds/final_translated.po"
    path.parent.mkdir(exist_ok=True)
    return write_latest_po(path, translation)


def _tag(root: Path, tag: str) -> None:
    subprocess.run(["git", "tag", tag], cwd=root, check=True)


def test_plans_initial_and_changed_revisions(workspace: Path) -> None:
    write_config(workspace / "translation-config.yml")
    _catalog(workspace, "譯文")
    commit = _commit(workspace)
    first = plan_locale_release(repo_root=workspace, published_tags=[])
    assert first == {
        "publish": True,
        "tag": "locale-zh_Hant-r1",
        "previous_tag": "",
        "commit": commit,
    }
    _tag(workspace, "locale-zh_Hant-r1")
    _tag(workspace, "locale-zh_Hant-r2")  # A tag without a published release is still reserved.
    _tag(workspace, "locale-de-r99")
    _catalog(workspace, "新譯文")
    _commit(workspace)
    result = plan_locale_release(repo_root=workspace, published_tags=["locale-zh_Hant-r1", "v99"])
    assert result["tag"] == "locale-zh_Hant-r3"
    assert result["previous_tag"] == "locale-zh_Hant-r1"
    pending = plan_locale_release(
        repo_root=workspace,
        published_tags=["locale-zh_Hant-r1"],
        reserved_tags=["locale-zh_Hant-r3"],
    )
    assert pending["tag"] == "locale-zh_Hant-r4"


def test_metadata_only_change_and_retry_do_not_publish(workspace: Path) -> None:
    write_config(workspace / "translation-config.yml")
    path = _catalog(workspace, "譯文")
    _commit(workspace)
    _tag(workspace, "locale-zh_Hant-r1")
    path.write_text(
        path.read_text().replace("Project-Id-Version:", "Project-Id-Version: new-header")
        + "\n# New comment\n",
        encoding="utf-8",
    )
    (workspace / "README.md").write_text("Documentation change\n", encoding="utf-8")
    _commit(workspace)
    for _ in range(2):
        result = plan_locale_release(repo_root=workspace, published_tags=["locale-zh_Hant-r1"])
        assert result["publish"] is False
        assert result["tag"] == ""


@pytest.mark.parametrize("change", ["clear", "fuzzy", "remove", "source"])
def test_loss_of_usable_translation_requires_release(workspace: Path, change: str) -> None:
    path = _catalog(workspace, "譯文")
    text = path.read_text()
    before = effective_translations(text, "zh_Hant")
    if change == "clear":
        after = _catalog(workspace, "").read_text()
    elif change == "fuzzy":
        after = text.replace('msgid "Source title"', '#, fuzzy\nmsgid "Source title"')
    elif change == "remove":
        after = text.replace('msgstr "譯文"', 'msgstr ""').replace("Source title", "Untranslated")
    else:
        after = text.replace("Source title", "New source")
    assert effective_translations(after, "zh_Hant") != before


def test_new_untranslated_source_does_not_change_effective_locale(workspace: Path) -> None:
    text = _catalog(workspace, "譯文").read_text()
    extra = '\n#: questions/22222222-2222-4222-8222-222222222222/title\nmsgid "Blank"\nmsgstr ""\n'
    assert effective_translations(text, "zh_Hant") == effective_translations(
        text + extra, "zh_Hant"
    )
