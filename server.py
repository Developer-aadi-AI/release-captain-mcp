"""
Minimal MCP server exposing ONE tool: create_release.

Wraps GitHub's REST API (POST /repos/{owner}/{repo}/releases). Creating a
release with a tag_name that doesn't exist yet makes GitHub create that tag
automatically — so this one call covers both "tag" and "release", no
separate tag-creation tool needed.

Run locally (stdio, for a quick sanity test):
    export GITHUB_TOKEN=ghp_xxx
    python server.py

Run for remote hosting (what TrueFoundry / any HTTP-based MCP client needs):
    export GITHUB_TOKEN=ghp_xxx
    export MCP_API_KEY=some-long-random-secret
    python server.py --http

MCP_API_KEY is a separate secret from GITHUB_TOKEN: it's what TrueFoundry (or
anyone) must present to call THIS server at all. Without it, this endpoint
would be open to anyone who finds the URL, who could then create releases
using your GitHub token. Set MCP_API_KEY before deploying anywhere public.
Callers must send: Authorization: Bearer <MCP_API_KEY>
"""

import os
import sys
import secrets
import httpx
import uvicorn
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
MCP_API_KEY = os.environ.get("MCP_API_KEY")

if not GITHUB_TOKEN:
    print("ERROR: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
    sys.exit(1)

mcp = FastMCP("github-release-server")


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Rejects any request that doesn't present the correct bearer token."""

    async def dispatch(self, request, call_next):
        auth_header = request.headers.get("authorization", "")
        expected = f"Bearer {MCP_API_KEY}"
        if not secrets.compare_digest(auth_header, expected):
            return JSONResponse(
                {"error": "unauthorized"},
                status_code=401,
            )
        return await call_next(request)


@mcp.tool()
async def create_release(
    owner: str,
    repo: str,
    tag_name: str,
    name: str,
    body: str,
    target_commitish: str = "main",
    draft: bool = False,
    prerelease: bool = False,
) -> dict:
    """
    Create a GitHub Release for a repository.

    If tag_name does not already exist on the repo, GitHub creates it
    automatically, pointing at target_commitish. This is the single
    irreversible write action this server exposes.

    Args:
        owner: repository owner (user or org)
        repo: repository name
        tag_name: the tag to create/use, e.g. "v1.2.0"
        name: the release title, e.g. "v1.2.0"
        body: the full release notes / changelog, in Markdown
        target_commitish: branch or commit SHA to tag (default "main")
        draft: create as a draft release (not publicly visible) if True
        prerelease: mark as a pre-release if True

    Returns:
        dict with success flag and either the created release's URL/id,
        or the raw error from GitHub on failure.
    """
    url = f"{GITHUB_API}/repos/{owner}/{repo}/releases"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {
        "tag_name": tag_name,
        "target_commitish": target_commitish,
        "name": name,
        "body": body,
        "draft": draft,
        "prerelease": prerelease,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload, timeout=30)

    if resp.status_code >= 400:
        return {
            "success": False,
            "status_code": resp.status_code,
            "error": resp.text,
        }

    data = resp.json()
    return {
        "success": True,
        "release_url": data.get("html_url"),
        "tag_name": data.get("tag_name"),
        "release_id": data.get("id"),
        "draft": data.get("draft"),
        "prerelease": data.get("prerelease"),
    }


if __name__ == "__main__":
    if "--http" in sys.argv:
        if not MCP_API_KEY:
            print(
                "WARNING: MCP_API_KEY is not set. This server will accept "
                "requests from ANYONE who can reach this URL. Set MCP_API_KEY "
                "before deploying this anywhere public.",
                file=sys.stderr,
            )
            app = mcp.streamable_http_app()
        else:
            app = mcp.streamable_http_app()
            app.add_middleware(ApiKeyMiddleware)

        port = int(os.environ.get("PORT", 8000))
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        mcp.run(transport="stdio")
