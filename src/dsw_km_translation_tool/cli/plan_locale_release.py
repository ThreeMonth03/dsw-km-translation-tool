"""Plan the next locale release without creating a tag or publishing assets."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from dsw_km_translation_tool.cli.github_outputs import append_github_outputs
from dsw_km_translation_tool.locale_release_plan import plan_locale_release


def main() -> None:
    """Read all published GitHub releases and emit the semantic release decision."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--repository", required=True, help="GitHub owner/repository")
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    result = subprocess.run(
        ["gh", "api", f"repos/{args.repository}/releases", "--paginate", "--slurp"],
        check=True,
        capture_output=True,
        text=True,
    )
    releases = [release for page in json.loads(result.stdout) for release in page]
    tags = [
        release["tag_name"]
        for release in releases
        if not release["draft"] and not release["prerelease"]
    ]
    plan = plan_locale_release(
        repo_root=args.repo_root,
        published_tags=tags,
        reserved_tags=[release["tag_name"] for release in releases],
    )
    append_github_outputs(output_path=args.github_output, values=plan)
    message = (
        f"Candidate locale release: `{plan['tag']}`. Validation must pass before publication."
        if plan["publish"]
        else f"No usable translation changes since `{plan['previous_tag'] or 'initial state'}`; publication skipped."
    )
    print(message)
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as handle:
            handle.write(message + "\n")


if __name__ == "__main__":
    main()
