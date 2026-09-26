# github-release-mcp

A minimal MCP (Model Context Protocol) server that exposes exactly one tool: **`create_release`**. It exists to give an agent (e.g. TrueFoundry's Release Captain) a single, narrow, auditable way to publish a GitHub Release — nothing more.

## Why this exists

GitHub's official MCP tooling exposes plenty of read operations (`list_tags`, `get_tag`, `list_commits`, `list_pull_requests`, …) but no direct tag-creation tool in some configurations. Rather than granting an agent broad repository write access to work around that, this server wraps a single, well-scoped API call:

```
POST /repos/{owner}/{repo}/releases
```

Creating a release with a `tag_name` that doesn't already exist makes GitHub create that tag automatically — so one call covers both "create the tag" and "create the release." No other write capability is exposed.

## What it does NOT do

- No tag deletion, no force-push, no branch operations
- No access to any repo other than what's passed as `owner`/`repo` per call
- No package registry publishing (npm, PyPI, etc.) — out of scope
- No unauthenticated access — every request must present a valid API key (see below)

## Requirements

- Python 3.11+
- A GitHub personal access token (fine-grained, scoped to the target repo(s), with **Contents: Read and write** permission)
- `mcp[cli]<2.0.0` — pinned deliberately. `mcp` 2.x renamed `FastMCP` to `MCPServer` and changed the API; this server is written against the 1.x `FastMCP` interface.

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `GITHUB_TOKEN` | Yes | Used by the server to call GitHub's API on your behalf |
| `MCP_API_KEY` | Required for `--http` mode | A separate secret callers must present to use this server at all. Without it, anyone who finds the URL could create releases using your GitHub token. |
| `PORT` | No (default `8000`) | Port to bind in `--http` mode; most hosting platforms set this automatically |

`GITHUB_TOKEN` and `MCP_API_KEY` protect two different things — never reuse one value for both.

## Running locally

Quick sanity check over stdio:
```bash
pip install "mcp[cli]<2.0.0" httpx
export GITHUB_TOKEN=ghp_xxx
python server.py
```

Over HTTP (what a remote MCP client like TrueFoundry needs):
```bash
export GITHUB_TOKEN=ghp_xxx
export MCP_API_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
python server.py --http
```

Verify it's up (expect a `406`, not a `404` or connection error — that confirms the MCP endpoint is live and correctly rejecting a plain GET):
```bash
curl -H "Authorization: Bearer $MCP_API_KEY" http://localhost:8000/mcp
```

Verify auth is actually enforced:
```bash
curl http://localhost:8000/mcp                                   # expect 401 (no key)
curl -H "Authorization: Bearer wrong" http://localhost:8000/mcp  # expect 401 (wrong key)
```

## Deploying (Docker)

```bash
docker build -t github-release-mcp .
docker run -p 8000:8000 \
  -e GITHUB_TOKEN=ghp_xxx \
  -e MCP_API_KEY=your-generated-secret \
  github-release-mcp
```

Set both environment variables on whatever platform hosts this (Render, Railway, Fly.io, etc.) — never hardcode them in the source.

## Security notes

- **DNS-rebinding protection is intentionally disabled** (`enable_dns_rebinding_protection=False` in `server.py`). The MCP SDK's default protection only allows `Host` headers matching `localhost`/`127.0.0.1`, which breaks the moment this is deployed under a real domain, and its `allowed_hosts` allowlist has no true wildcard (a bare `"*"` matches nothing — only exact hostnames or a `host:*` port-wildcard pattern). Since every request already requires a valid `MCP_API_KEY` via `ApiKeyMiddleware`, that bearer-token check is the real access control here, making the SDK's host-based protection redundant for this deployment.
- **Constant-time comparison**: the API key check uses `secrets.compare_digest`, not `==`, to avoid timing side-channels.
- **Rotate `MCP_API_KEY` and `GITHUB_TOKEN`** if either is ever pasted into a chat, committed to git, or otherwise exposed — treat any exposed secret as compromised immediately, don't wait for evidence of misuse.

## Registering with TrueFoundry

Connectors → Add MCP server:
- **URL:** `https://<your-deployed-host>/<path>/mcp`
- **Auth type:** API Key
- **API Key:** the same value as `MCP_API_KEY`

Once added, mark `create_release` as a **checkpointed** (requires human approval) tool in the agent builder — this server has no concept of approval on its own; that gate lives entirely on the platform side.
