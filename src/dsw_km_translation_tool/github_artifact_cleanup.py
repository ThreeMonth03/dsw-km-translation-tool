"""Delete allowlisted artifacts belonging exclusively to merged pull requests."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from collections import Counter
from fnmatch import fnmatchcase
from pathlib import Path


class GitHubError(RuntimeError):
    """An API request failed without making its response trustworthy."""


class GitHub:
    def __init__(self, repository: str) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("Expected an owner/repository name")
        self.repository = repository

    def request(self, path: str, *, paginate: bool = False, delete: bool = False):
        command = ["gh", "api", f"repos/{self.repository}/{path}"]
        if paginate:
            command.extend(["--paginate", "--slurp"])
        if delete:
            command.extend(["--method", "DELETE"])
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if result.returncode:
            if delete and "(HTTP 404)" in result.stderr:
                return False
            raise GitHubError(f"GitHub API request failed: {path}\n{result.stderr.strip()}")
        if delete:
            return True
        return json.loads(result.stdout)

    def artifacts(self):
        pages = self.request("actions/artifacts?per_page=100", paginate=True)
        return [item for page in pages for item in page["artifacts"]]

    def run(self, run_id: int):
        return self.request(f"actions/runs/{run_id}")

    def pull(self, number: int):
        return self.request(f"pulls/{number}")

    def associated_pulls(self, sha: str):
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise ValueError("Unexpected workflow commit SHA")
        pages = self.request(f"commits/{sha}/pulls?per_page=100", paginate=True)
        return [item for page in pages for item in page]

    def delete(self, artifact_id: int):
        return self.request(f"actions/artifacts/{artifact_id}", delete=True)


def positive_id(value) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError("Unexpected GitHub object ID")
    return value


class Cleaner:
    def __init__(self, api, patterns: list[str]) -> None:
        if not patterns or any(not pattern.strip() or pattern == "*" for pattern in patterns):
            raise ValueError("Provide explicit artifact names or prefixes, not '*'")
        self.api = api
        self.patterns = patterns
        self.runs = {}
        self.pulls = {}
        self.associations = {}

    def eligible_run(self, run_id: int, *, refresh: bool = False) -> tuple[bool, str]:
        if refresh or run_id not in self.runs:
            self.runs[run_id] = self.api.run(run_id)
        run = self.runs[run_id]
        if run["id"] != run_id:
            raise ValueError("Workflow run ID does not match the request")
        if run["event"] != "pull_request":
            return False, "not-pr"
        if run["status"] != "completed":
            return False, "running"
        associated = run.get("pull_requests", [])
        if not associated:
            sha = run["head_sha"]
            if refresh or sha not in self.associations:
                self.associations[sha] = self.api.associated_pulls(sha)
            associated = self.associations[sha]
        if not associated:
            return False, "unknown-pr"
        for entry in associated:
            number = positive_id(entry["number"])
            if refresh or number not in self.pulls:
                self.pulls[number] = self.api.pull(number)
            pull = self.pulls[number]
            if pull["number"] != number:
                raise ValueError("Pull request number does not match the request")
            if pull["base"]["repo"]["full_name"].lower() != self.api.repository.lower():
                return False, "other-repository"
            if pull["state"] != "closed" or not pull["merged"] or not pull["merged_at"]:
                return False, "unmerged-pr"
        return True, "merged-pr"

    def plan(self) -> dict:
        selected = []
        skipped = Counter()
        for artifact in self.api.artifacts():
            if artifact["expired"]:
                skipped["expired"] += 1
                continue
            if not any(fnmatchcase(artifact["name"], pattern) for pattern in self.patterns):
                skipped["not-allowlisted"] += 1
                continue
            run_id = positive_id(artifact["workflow_run"]["id"])
            eligible, reason = self.eligible_run(run_id)
            if not eligible:
                skipped[reason] += 1
                continue
            selected.append(
                {
                    "id": positive_id(artifact["id"]),
                    "run_id": run_id,
                    "name": artifact["name"],
                    "bytes": artifact["size_in_bytes"],
                }
            )
        return {
            "repository": self.api.repository,
            "artifacts": selected,
            "skipped": dict(skipped),
        }

    def apply(self, plan: dict, *, limit: int) -> dict:
        if plan["repository"] != self.api.repository or limit <= 0:
            raise ValueError("Invalid cleanup plan or deletion limit")
        deleted = []
        absent = []
        deferred = []
        for index, artifact in enumerate(plan["artifacts"]):
            if index >= limit:
                deferred.append(artifact["id"])
                continue
            run_id = artifact["run_id"]
            # A historical run can be re-run between inventory and deletion.
            # Recheck it immediately before each deletion, without using cached state.
            eligible, _ = self.eligible_run(run_id, refresh=True)
            if not eligible:
                deferred.append(artifact["id"])
                continue
            started = time.monotonic()
            if self.api.delete(artifact["id"]):
                deleted.append(artifact["id"])
            else:
                absent.append(artifact["id"])
            print(
                json.dumps({"artifact_id": artifact["id"], "run_id": run_id}),
                flush=True,
            )
            time.sleep(max(0, 1 - (time.monotonic() - started)))
        return {"deleted": deleted, "already_absent": absent, "deferred": deferred}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--artifact-pattern", action="append", required=True)
    parser.add_argument(
        "--apply", action="store_true", help="Delete artifacts; default is dry-run."
    )
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    if not 1 <= args.limit <= 100:
        parser.error("--limit must be between 1 and 100")
    cleaner = Cleaner(GitHub(args.repository), args.artifact_pattern)
    plan = cleaner.plan()
    print(
        json.dumps({"mode": "apply" if args.apply else "dry-run", **plan}, indent=2),
        flush=True,
    )
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as report:
            report.write(
                "## Merged PR artifact cleanup\n\n"
                f"Mode: {'apply' if args.apply else 'dry-run'}. "
                f"Eligible artifacts: {len(plan['artifacts'])}. "
                f"Maximum deletions: {args.limit}.\n\n"
                "Only allowlisted artifacts from completed PR runs are eligible. "
                "Releases, workflow runs, and logs are not deleted.\n"
            )
    if args.apply:
        result = cleaner.apply(plan, limit=args.limit)
        print(json.dumps(result, indent=2), flush=True)
        if summary:
            with Path(summary).open("a", encoding="utf-8") as report:
                report.write(
                    f"\nDeleted: {len(result['deleted'])}; "
                    f"already absent: {len(result['already_absent'])}; "
                    f"deferred: {len(result['deferred'])}.\n"
                )


if __name__ == "__main__":
    main()
