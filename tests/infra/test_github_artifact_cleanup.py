"""Artifact cleanup must not guess PR ownership or delete release/run records."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from dsw_km_translation_tool import github_artifact_cleanup as cleanup


class FakeGitHub:
    repository = "owner/repo"

    def __init__(self):
        self.items = [
            {
                "id": 11,
                "name": "review",
                "expired": False,
                "size_in_bytes": 100,
                "workflow_run": {"id": 22},
            }
        ]
        self.run_data = {
            "id": 22,
            "event": "pull_request",
            "status": "completed",
            "head_sha": "a" * 40,
            "pull_requests": [{"number": 33}],
        }
        self.pull_data = {
            "number": 33,
            "state": "closed",
            "merged": True,
            "merged_at": "2026-09-01T00:00:00Z",
            "base": {"repo": {"full_name": self.repository}},
        }
        self.associated = [{"number": 33}]
        self.deleted = []

    def artifacts(self):
        return deepcopy(self.items)

    def run(self, _run_id):
        return deepcopy(self.run_data)

    def pull(self, number):
        return {**deepcopy(self.pull_data), "number": number}

    def associated_pulls(self, _sha):
        return deepcopy(self.associated)

    def delete(self, artifact_id):
        if artifact_id in self.deleted:
            return False
        self.deleted.append(artifact_id)
        return True


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(cleanup.time, "sleep", lambda _: None)
    return FakeGitHub()


def test_plan_is_read_only_and_apply_deletes_only_artifact(api):
    cleaner = cleanup.Cleaner(api, ["review"])
    plan = cleaner.plan()
    assert [a["id"] for a in plan["artifacts"]] == [11]
    assert not api.deleted
    assert cleaner.apply(plan, limit=100) == {
        "deleted": [11],
        "already_absent": [],
        "deferred": [],
    }
    assert cleaner.apply(plan, limit=100)["already_absent"] == [11]


@pytest.mark.parametrize("event", ["push", "schedule", "workflow_dispatch", "workflow_run"])
def test_non_pr_runs_are_never_deleted(api, event):
    api.run_data["event"] = event
    assert cleanup.Cleaner(api, ["review"]).plan()["artifacts"] == []


@pytest.mark.parametrize("status", ["queued", "in_progress", "waiting", "requested"])
def test_running_jobs_are_preserved(api, status):
    api.run_data["status"] = status
    assert cleanup.Cleaner(api, ["review"]).plan()["skipped"] == {"running": 1}


def test_rerun_after_inventory_is_preserved(api):
    cleaner = cleanup.Cleaner(api, ["review"])
    plan = cleaner.plan()
    api.run_data["status"] = "in_progress"
    assert cleaner.apply(plan, limit=100)["deferred"] == [11]
    assert not api.deleted


@pytest.mark.parametrize(
    "changes",
    [
        {"state": "open"},
        {"merged": False},
        {"merged_at": None},
        {"base": {"repo": {"full_name": "another/repo"}}},
    ],
)
def test_unmerged_or_foreign_pulls_are_preserved(api, changes):
    api.pull_data.update(changes)
    assert cleanup.Cleaner(api, ["review"]).plan()["artifacts"] == []


def test_missing_run_pr_metadata_is_resolved_by_commit(api):
    api.run_data["pull_requests"] = []
    assert len(cleanup.Cleaner(api, ["review"]).plan()["artifacts"]) == 1


def test_unknown_pr_is_not_guessed_from_branch_or_name(api):
    api.run_data.update(pull_requests=[], head_branch="merged-branch")
    api.associated = []
    assert cleanup.Cleaner(api, ["review"]).plan()["skipped"] == {"unknown-pr": 1}


def test_shared_commit_requires_all_associated_prs_to_be_merged(api):
    api.run_data["pull_requests"] = []
    api.associated.append({"number": 34})
    original = api.pull
    api.pull = lambda number: {**original(number), "merged": number == 33}
    assert cleanup.Cleaner(api, ["review"]).plan()["artifacts"] == []


def test_expired_and_nonallowlisted_artifacts_are_preserved(api):
    api.items.extend(
        [
            {**api.items[0], "id": 12, "name": "release-input"},
            {**api.items[0], "id": 13, "expired": True},
        ]
    )
    plan = cleanup.Cleaner(api, ["review"]).plan()
    assert [item["id"] for item in plan["artifacts"]] == [11]
    assert plan["skipped"] == {"not-allowlisted": 1, "expired": 1}


def test_delete_limit_defers_remaining_artifacts(api):
    api.items.append({**api.items[0], "id": 12})
    cleaner = cleanup.Cleaner(api, ["review"])
    assert cleaner.apply(cleaner.plan(), limit=1)["deferred"] == [12]
    assert api.deleted == [11]


@pytest.mark.parametrize("patterns", [[], [""], ["*"]])
def test_empty_or_unbounded_allowlist_is_rejected(api, patterns):
    with pytest.raises(ValueError):
        cleanup.Cleaner(api, patterns)


def test_metadata_errors_fail_without_deleting(api):
    api.run_data["id"] = 99
    with pytest.raises(ValueError, match="run ID"):
        cleanup.Cleaner(api, ["review"]).plan()
    assert not api.deleted


def test_github_pagination_and_delete_are_scoped(monkeypatch):
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        assert kwargs["timeout"] == 60
        return SimpleNamespace(returncode=0, stdout='[{"artifacts":[]}]', stderr="")

    monkeypatch.setattr(cleanup.subprocess, "run", run)
    github = cleanup.GitHub("owner/repo")
    assert github.artifacts() == []
    assert commands[0] == [
        "gh",
        "api",
        "repos/owner/repo/actions/artifacts?per_page=100",
        "--paginate",
        "--slurp",
    ]
    assert github.delete(11)
    assert commands[-1] == [
        "gh",
        "api",
        "repos/owner/repo/actions/artifacts/11",
        "--method",
        "DELETE",
    ]


def test_only_delete_404_is_idempotent(monkeypatch):
    monkeypatch.setattr(
        cleanup.subprocess,
        "run",
        lambda *_a, **_k: SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="gh: Not Found (HTTP 404)",
        ),
    )
    github = cleanup.GitHub("owner/repo")
    assert github.delete(11) is False
    with pytest.raises(cleanup.GitHubError):
        github.pull(33)


def test_cli_dry_run_is_the_default(api, monkeypatch):
    monkeypatch.setattr(cleanup, "GitHub", lambda _repo: api)
    monkeypatch.setattr(
        "sys.argv",
        ["cleanup", "--repository", api.repository, "--artifact-pattern", "review"],
    )
    cleanup.main()
    assert not api.deleted
