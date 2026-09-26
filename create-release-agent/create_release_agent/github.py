from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

import requests

API = "https://api.github.com"


@dataclass(frozen=True)
class TagInfo:
    name: str
    sha: str
    type: str
    date: datetime | None = None


@dataclass(frozen=True)
class CommitInfo:
    sha: str
    message: str
    url: str
    date: datetime | None


@dataclass(frozen=True)
class PullRequestInfo:
    number: int
    title: str
    url: str
    merged_at: datetime | None


class GitHubClient:
    def __init__(self, owner: str, repo: str, token: str):
        self.owner = owner
        self.repo = repo
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "create-release-agent/0.1.0",
            }
        )

    def _url(self, path: str) -> str:
        return f"{API}/repos/{self.owner}/{self.repo}{path}"

    def request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        resp = self.session.request(method, self._url(path), timeout=30, **kwargs)
        resp.raise_for_status()
        return resp

    def get_repo(self) -> dict[str, Any]:
        return self.request("GET", "").json()

    def list_tags(self, per_page: int = 100, page: int = 1) -> list[dict[str, Any]]:
        return self.request("GET", f"/tags?per_page={per_page}&page={page}").json()

    def get_ref_tag(self, tag: str) -> dict[str, Any]:
        return self.request("GET", f"/git/ref/tags/{tag}").json()

    def get_git_tag(self, sha: str) -> dict[str, Any]:
        return self.request("GET", f"/git/tags/{sha}").json()

    def get_commit(self, sha: str) -> dict[str, Any]:
        return self.request("GET", f"/commits/{sha}").json()

    def list_commits(
        self,
        sha: str | None = None,
        per_page: int = 100,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        query = [f"per_page={per_page}", f"page={page}"]
        if sha:
            query.append(f"sha={sha}")
        return self.request("GET", f"/commits?{'&'.join(query)}").json()

    def compare(self, base: str, head: str) -> dict[str, Any]:
        return self.request("GET", f"/compare/{base}...{head}").json()

    def list_pull_requests(
        self,
        state: str = "closed",
        base: str | None = None,
        per_page: int = 100,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        query = [f"state={state}", f"per_page={per_page}", f"page={page}"]
        if base:
            query.append(f"base={base}")
        return self.request("GET", f"/pulls?{'&'.join(query)}").json()

    def create_release(
        self,
        tag_name: str,
        name: str,
        body: str,
        target_commitish: str,
        draft: bool = False,
        prerelease: bool = False,
    ) -> dict[str, Any]:
        payload = {
            "tag_name": tag_name,
            "target_commitish": target_commitish,
            "name": name,
            "body": body,
            "draft": draft,
            "prerelease": prerelease,
        }
        return self.request("POST", "/releases", json=payload).json()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def latest_tag(client: GitHubClient) -> TagInfo | None:
    tags = client.list_tags()
    if not tags:
        return None
    first = tags[0]
    name = first["name"]
    ref = client.get_ref_tag(name)
    obj = ref["object"]
    sha = obj["sha"]
    obj_type = obj.get("type", "commit")

    date: datetime | None = None
    if obj_type == "tag":
        tag = client.get_git_tag(sha)
        date = parse_datetime(tag.get("tagger", {}).get("date"))
        sha = tag["object"]["sha"]
        obj_type = tag["object"].get("type", "commit")
    if obj_type == "commit":
        commit = client.get_commit(sha)
        date = parse_datetime(commit.get("commit", {}).get("committer", {}).get("date"))
    return TagInfo(name=name, sha=sha, type=obj_type, date=date)


def commits_since_tag(client: GitHubClient, tag: TagInfo | None, default_branch: str) -> list[CommitInfo]:
    out: list[CommitInfo] = []
    if tag is None:
        page = 1
        while True:
            items = client.list_commits(sha=default_branch, page=page)
            if not items:
                break
            for item in items:
                out.append(
                    CommitInfo(
                        sha=item["sha"],
                        message=item["commit"]["message"].splitlines()[0],
                        url=item["html_url"],
                        date=parse_datetime(item["commit"]["committer"]["date"]),
                    )
                )
            if len(items) < 100:
                break
            page += 1
        return list(reversed(out))

    compare = client.compare(tag.name, default_branch)
    for item in compare.get("commits", []):
        out.append(
            CommitInfo(
                sha=item["sha"],
                message=item["commit"]["message"].splitlines()[0],
                url=item["html_url"],
                date=parse_datetime(item["commit"]["committer"]["date"]),
            )
        )
    return out


def merged_prs_since_tag(client: GitHubClient, tag: TagInfo | None, base_branch: str) -> list[PullRequestInfo]:
    since = tag.date if tag else None
    out: list[PullRequestInfo] = []
    page = 1
    while True:
        items = client.list_pull_requests(state="closed", base=base_branch, page=page)
        if not items:
            break
        for item in items:
            merged_at = parse_datetime(item.get("merged_at"))
            if not merged_at:
                continue
            if since and merged_at < since:
                continue
            out.append(
                PullRequestInfo(
                    number=item["number"],
                    title=item["title"],
                    url=item["html_url"],
                    merged_at=merged_at,
                )
            )
        if len(items) < 100:
            break
        page += 1
    return out
