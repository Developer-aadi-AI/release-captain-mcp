from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from .changelog import build_entries, compute_next_version, render_changelog
from .github import GitHubClient, commits_since_tag, latest_tag, merged_prs_since_tag
from .tests import run_validation


def _print_draft(owner: str, repo: str, current: str | None, proposed: str, tests: str, body: str) -> None:
    print(f"REPO: {owner}/{repo}")
    print(f"CURRENT VERSION (latest tag): {current or 'none'}")
    print(f"PROPOSED VERSION: {proposed}")
    print(f"TESTS: {tests}")
    print()
    print("CHANGELOG")
    print(body)


def draft_release(owner: str, repo: str, token: str) -> tuple[str | None, str, str]:
    client = GitHubClient(owner, repo, token)
    repo_info = client.get_repo()
    default_branch = repo_info.get("default_branch", "main")

    tag = latest_tag(client)
    commits = commits_since_tag(client, tag, default_branch)
    prs = merged_prs_since_tag(client, tag, default_branch)
    entries = build_entries(commits, prs)
    proposed = compute_next_version(tag.name if tag else None, entries)
    body = render_changelog(entries, f"{owner}/{repo}")
    current = tag.name if tag else None
    return current, proposed, body


def cmd_draft(args: argparse.Namespace) -> int:
    current, proposed, body = draft_release(args.owner, args.repo, args.token)
    tests = "not run (draft only)"
    _print_draft(args.owner, args.repo, current, proposed, tests, body)
    return 0


def cmd_release(args: argparse.Namespace) -> int:
    current, proposed, body = draft_release(args.owner, args.repo, args.token)

    if args.run_tests:
        result = run_validation(Path(args.repo_path))
        tests = f"{('PASS' if result.returncode == 0 else 'FAIL')} (exit code {result.returncode})"
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr)
            raise SystemExit(1)
    else:
        tests = "not run (use --run-tests to validate a local checkout first)"

    _print_draft(args.owner, args.repo, current, proposed, tests, body)

    if not args.yes:
        answer = input("Create this release? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Aborted by user.")
            return 1

    client = GitHubClient(args.owner, args.repo, args.token)
    release = client.create_release(
        tag_name=f"v{proposed}",
        name=f"v{proposed}",
        body=body,
        target_commitish=args.target_commitish,
        draft=False,
        prerelease=args.prerelease,
    )
    print(release.get("html_url", "Release created."))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="create-release-agent")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--owner", required=True)
        p.add_argument("--repo", required=True)
        p.add_argument("--token", required=True, help="GitHub token with repo read/write access")

    draft = sub.add_parser("draft", help="Draft a release without publishing it")
    add_common(draft)
    draft.set_defaults(func=cmd_draft)

    release = sub.add_parser("release", help="Draft and create a GitHub Release")
    add_common(release)
    release.add_argument("--yes", action="store_true", help="Skip the approval prompt")
    release.add_argument("--run-tests", action="store_true", help="Run local validation before releasing")
    release.add_argument("--repo-path", default=".", help="Local repository path for validation")
    release.add_argument("--target-commitish", default="main")
    release.add_argument("--prerelease", action="store_true")
    release.set_defaults(func=cmd_release)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(args.func(args))
