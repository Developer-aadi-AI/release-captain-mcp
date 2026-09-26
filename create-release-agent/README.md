# Create Release Agent

A standalone, clean-room implementation of a release-captain style agent.

It can:
- inspect a GitHub repository
- find the latest tag
- collect commits and merged pull requests since that tag
- draft a release note grouped into Added / Fixed / Breaking / Chores
- prompt for approval
- create the GitHub Release through the GitHub Releases API

## Install

```bash
pip install -e .
```

## Run tests

```bash
pip install -e . pytest
pytest -q
```

## Usage

Draft only:

```bash
create-release-agent draft --owner OWNER --repo REPO --token ghp_xxx
```

Draft and publish after confirmation:

```bash
create-release-agent release --owner OWNER --repo REPO --token ghp_xxx
```

Non-interactive publish:

```bash
create-release-agent release --owner OWNER --repo REPO --token ghp_xxx --yes
```

## Docker

```bash
docker build -t create-release-agent .
docker run --rm create-release-agent draft --owner OWNER --repo REPO --token ghp_xxx
```

## Notes

- This project is intentionally self-contained and does not rely on hidden assistant internals.
- It uses the GitHub REST API directly.
- In a no-tag repository, it proposes `0.1.0` as the first usable release.
