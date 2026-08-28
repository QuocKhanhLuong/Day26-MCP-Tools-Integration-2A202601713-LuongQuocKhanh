"""Authenticated Streamable HTTP version of the log-inspector MCP server."""

from __future__ import annotations

import json
import os
import secrets

from pydantic import AnyHttpUrl

from mcp.server import MCPServer
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings

from core import (
    get_recent_errors_v1,
    search_logs_v1,
    search_logs_v2 as search_logs_v2_core,
    server_metadata_json,
)

PORT = int(os.getenv("MCP_PORT", "8000"))
HOST = os.getenv("MCP_HOST", "0.0.0.0")
PUBLIC_ORIGIN = os.getenv("MCP_PUBLIC_URL", f"http://127.0.0.1:{PORT}").rstrip("/")
RESOURCE_URL = f"{PUBLIC_ORIGIN}/mcp"
ISSUER_URL = os.getenv("MCP_ISSUER_URL", "https://auth.example.com")


class EnvTokenVerifier(TokenVerifier):
    """Verify one bearer token loaded only from MCP_AUTH_TOKEN."""

    async def verify_token(self, token: str) -> AccessToken | None:
        expected = os.getenv("MCP_AUTH_TOKEN")
        if not expected or not secrets.compare_digest(token, expected):
            return None
        return AccessToken(
            token=token,
            client_id="day26-log-inspector-client",
            scopes=["logs:read"],
        )


mcp = MCPServer(
    "log-inspector-http",
    instructions="Authenticated Streamable HTTP log-inspection server.",
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(ISSUER_URL),
        resource_server_url=AnyHttpUrl(RESOURCE_URL),
        required_scopes=["logs:read"],
    ),
    token_verifier=EnvTokenVerifier(),
)


@mcp.tool()
def search_logs(
    keyword: str,
    log_file: str = "sample.log",
    limit: int = 50,
    case_sensitive: bool = False,
) -> list[str]:
    """[v1] Find log lines containing a keyword. Kept for old clients."""
    return search_logs_v1(log_file, keyword, limit, case_sensitive)


@mcp.tool()
def get_recent_errors(
    limit: int = 10,
    log_file: str = "sample.log",
    include_warnings: bool = False,
) -> list[str]:
    """Return newest ERROR/CRITICAL entries; optionally include warnings."""
    return get_recent_errors_v1(log_file, limit, include_warnings)


@mcp.tool()
def search_logs_v2(
    keyword: str,
    log_file: str = "sample.log",
    limit: int = 50,
    case_sensitive: bool = False,
) -> str:
    """[v2] Return structured JSON without changing the v1 response contract."""
    result = search_logs_v2_core(log_file, keyword, limit, case_sensitive)
    return json.dumps(result, ensure_ascii=False)


@mcp.resource("server://info")
def server_info() -> str:
    """Server metadata used by capability-aware clients before selecting a tool."""
    return server_metadata_json()


def main() -> None:
    if not os.getenv("MCP_AUTH_TOKEN"):
        raise SystemExit(
            "MCP_AUTH_TOKEN is required. Set it in your shell; never commit it to Git."
        )
    mcp.run(transport="streamable-http", host=HOST, port=PORT)


if __name__ == "__main__":
    main()
