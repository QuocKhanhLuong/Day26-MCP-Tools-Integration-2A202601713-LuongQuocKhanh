"""Local stdio MCP server for the Day26 submission."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from core import (
    get_recent_errors_v1,
    search_logs_v1,
    search_logs_v2 as search_logs_v2_core,
    server_metadata_json,
)

mcp = FastMCP(
    "log-inspector",
    instructions=(
        "Inspect local text logs under LOG_INSPECTOR_ROOT. "
        "Use search_logs for backward-compatible text results, "
        "get_recent_errors for newest failures, and search_logs_v2 for structured output."
    ),
)


@mcp.tool()
def search_logs(
    keyword: str,
    log_file: str = "sample.log",
    limit: int = 50,
    case_sensitive: bool = False,
) -> list[str]:
    """[v1] Find lines containing a keyword inside a configured local log file.

    Args:
        keyword: Text to search for, for example ERROR, timeout, CUDA, or request_id.
        log_file: File name relative to LOG_INSPECTOR_ROOT.
        limit: Maximum number of matching lines to return (1-500).
        case_sensitive: Whether keyword matching should preserve case.
    """
    return search_logs_v1(log_file, keyword, limit, case_sensitive)


@mcp.tool()
def get_recent_errors(
    limit: int = 10,
    log_file: str = "sample.log",
    include_warnings: bool = False,
) -> list[str]:
    """Return the newest ERROR/CRITICAL lines from a log file.

    Args:
        limit: Number of newest failures to return (1-500).
        log_file: File name relative to LOG_INSPECTOR_ROOT.
        include_warnings: Include WARNING/WARN lines in addition to errors.
    """
    return get_recent_errors_v1(log_file, limit, include_warnings)


@mcp.tool()
def search_logs_v2(
    keyword: str,
    log_file: str = "sample.log",
    limit: int = 50,
    case_sensitive: bool = False,
) -> str:
    """[v2] Search logs and return structured JSON with parsed metadata.

    This is additive: the v1 search_logs tool remains available so old clients
    keep working without code changes.
    """
    result = search_logs_v2_core(log_file, keyword, limit, case_sensitive)
    return json.dumps(result, ensure_ascii=False)


@mcp.resource("server://info")
def server_info() -> str:
    """Publish server version, capabilities, tool versions, and compatibility notes."""
    return server_metadata_json()


if __name__ == "__main__":
    mcp.run()
