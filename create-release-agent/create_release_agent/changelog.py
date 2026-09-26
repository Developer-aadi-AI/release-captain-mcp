from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Iterable

from .github import CommitInfo, PullRequestInfo


class Section(str, Enum):
    ADDED = "Added"
    FIXED = "Fixed"
    BREAKING = "Breaking"
    CHORES = "Chores"


@dataclass(frozen=True)
class Entry:
    section: Section
    text: str
    ref: str


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


def classify(text: str) -> Section:
    lowered = text.lower().strip()
    if "breaking change" in lowered or re.match(r"^(?:feat|fix|refactor|perf|chore|docs|ci|build)(!:|\!)", lowered):
        return Section.BREAKING
    if re.match(r"^(feat|feature)(\(|:|\s)", lowered) or lowered.startswith("add ") or lowered.startswith("adding "):
        return Section.ADDED
    if re.match(r"^fix(\(|:|\s)", lowered) or lowered.startswith("bugfix"):
        return Section.FIXED
    if lowered.startswith(("deps", "dependency", "chore", "docs", "ci", "build", "refactor", "style", "test")):
        return Section.CHORES
    return Section.CHORES


def _entry_text(title: str) -> str:
    title = title.strip()
    for prefix in ("feat:", "feat(", "fix:", "fix(", "chore:", "docs:", "ci:", "build:"):
        if title.lower().startswith(prefix):
            return title.split(":", 1)[-1].strip() if ":" in title else title
    return title


def build_entries(commits: Iterable[CommitInfo], prs: Iterable[PullRequestInfo]) -> list[Entry]:
    seen: set[str] = set()
    entries: list[Entry] = []

    def add(text: str, ref: str) -> None:
        key = _norm(text)
        if not text or key in seen:
            return
        seen.add(key)
        entries.append(Entry(section=classify(text), text=text, ref=ref))

    for c in commits:
        add(_entry_text(c.message), c.url)
    for p in prs:
        add(_entry_text(p.title), p.url)
    return entries


def render_changelog(entries: Iterable[Entry], repo: str) -> str:
    grouped = {s: [] for s in Section}
    for entry in entries:
        grouped[entry.section].append(entry)

    parts = [f"# Release notes for {repo}"]
    for section in (Section.ADDED, Section.FIXED, Section.BREAKING, Section.CHORES):
        items = grouped[section]
        if not items:
            continue
        parts.append(f"\n## {section.value}")
        for item in items:
            parts.append(f"- {item.text}")
    return "\n".join(parts).strip() + "\n"


def _parse_semver(tag: str) -> tuple[int, int, int]:
    tag = tag.lstrip("v")
    major, minor, patch = tag.split(".")[:3]
    return int(major), int(minor), int(patch)


def compute_next_version(latest_tag: str | None, entries: Iterable[Entry]) -> str:
    sections = {entry.section for entry in entries}
    if not latest_tag:
        return "0.1.0"
    major, minor, patch = _parse_semver(latest_tag)
    if Section.BREAKING in sections:
        return f"{major + 1}.0.0"
    if Section.ADDED in sections:
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"
