"""Prepare native locale assets for one immutable translation revision."""

from __future__ import annotations

import argparse
from pathlib import Path

from dsw_km_translation_tool.locale_release import prepare_locale_release


def main() -> None:
    """Build and validate release assets without publishing them."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--tooling-repo", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("translation-config.yml"))
    parser.add_argument("--tag", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    manifest = prepare_locale_release(
        repo_root=args.repo_root,
        tooling_repo=args.tooling_repo,
        tag=args.tag,
        output_dir=args.out,
        config_path=args.config,
    )
    print(f"Prepared {manifest['tag']} in {args.out}")


if __name__ == "__main__":
    main()
