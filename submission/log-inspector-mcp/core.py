"""Core log-inspection logic shared by the MCP servers.

This module intentionally has no MCP dependency so the business logic can be
unit-tested independently from the transport layer.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_LOG_ROOT = Path(
    os.getenv("LOG_INSPECTOR_ROOT", str(BASE_DIR / "data"))
).expanduser().resolve()

_LOG_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?)\s+"
    r"(?:\[(?P<bracket_level>[A-Za-z]+)\]|(?P<plain_level>[A-Za-z]+))\s+"
    r"(?P<message>.*)$"
)


def _clamp_limit(limit: int, *, maximum: int = 500) -> int:
    if limit < 1:
        raise ValueError("limit must be >= 1")
    return min(limit, maximum)


def resolve_log_path(log_file: str, *, root: Path | None = None) -> Path:
    """Resolve a log file while preventing traversal outside the configured root."""
    root_path = (root or DEFAULT_LOG_ROOT).expanduser().resolve()
    candidate = Path(log_file).expanduser()
    if not candidate.is_absolute():
        candidate = root_path / candidate
    candidate = candidate.resolve()

    try:
        candidate.relative_to(root_path)
    except ValueError as exc:
        raise ValueError(
            f"log_file must stay inside LOG_INSPECTOR_ROOT ({root_path})"
        ) from exc

    if not candidate.exists():
        raise FileNotFoundError(f"log file does not exist: {candidate}")
    if not candidate.is_file():
        raise ValueError(f"log path is not a file: {candidate}")
    return candidate


def _read_lines(log_file: str, *, root: Path | None = None) -> list[str]:
    path = resolve_log_path(log_file, root=root)
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def search_logs_v1(
    log_file: str,
    keyword: str,
    limit: int = 50,
    case_sensitive: bool = False,
    *,
    root: Path | None = None,
) -> list[str]:
    """Legacy search result: a list of matching source lines with line numbers."""
    limit = _clamp_limit(limit)
    if not keyword.strip():
        raise ValueError("keyword must not be empty")

    needle = keyword if case_sensitive else keyword.casefold()
    matches: list[str] = []
    for line_number, line in enumerate(_read_lines(log_file, root=root), start=1):
        haystack = line if case_sensitive else line.casefold()
        if needle in haystack:
            matches.append(f"{line_number}: {line}")
            if len(matches) >= limit:
                break
    return matches


def get_recent_errors_v1(
    log_file: str,
    limit: int = 10,
    include_warnings: bool = False,
    *,
    root: Path | None = None,
) -> list[str]:
    """Return newest ERROR/CRITICAL lines; optionally include WARNING/WARN."""
    limit = _clamp_limit(limit)
    accepted = {"ERROR", "CRITICAL"}
    if include_warnings:
        accepted.update({"WARNING", "WARN"})

    lines = _read_lines(log_file, root=root)
    results: list[str] = []
    for line_number in range(len(lines), 0, -1):
        line = lines[line_number - 1]
        parsed = parse_log_line(line)
        level = parsed.get("level")
        if isinstance(level, str) and level.upper() in accepted:
            results.append(f"{line_number}: {line}")
            if len(results) >= limit:
                break
    return results


def parse_log_line(line: str) -> dict[str, Any]:
    """Parse a conventional timestamp + level log line without rejecting free text."""
    match = _LOG_PATTERN.match(line)
    if not match:
        return {"timestamp": None, "level": None, "message": line}

    level = match.group("bracket_level") or match.group("plain_level")
    return {
        "timestamp": match.group("timestamp"),
        "level": level.upper() if level else None,
        "message": match.group("message"),
    }


def search_logs_v2(
    log_file: str,
    keyword: str,
    limit: int = 50,
    case_sensitive: bool = False,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """Structured v2 search with metadata and parsed fields."""
    limit = _clamp_limit(limit)
    if not keyword.strip():
        raise ValueError("keyword must not be empty")

    path = resolve_log_path(log_file, root=root)
    needle = keyword if case_sensitive else keyword.casefold()
    entries: list[dict[str, Any]] = []
    total_matches = 0

    for line_number, line in enumerate(
        path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
    ):
        haystack = line if case_sensitive else line.casefold()
        if needle not in haystack:
            continue

        total_matches += 1
        if len(entries) >= limit:
            continue

        parsed = parse_log_line(line)
        entries.append(
            {
                "line_number": line_number,
                "timestamp": parsed["timestamp"],
                "level": parsed["level"],
                "message": parsed["message"],
                "raw": line,
            }
        )

    return {
        "api_version": "2.0",
        "file": path.name,
        "query": {
            "keyword": keyword,
            "case_sensitive": case_sensitive,
            "limit": limit,
        },
        "matched": total_matches,
        "returned": len(entries),
        "truncated": total_matches > len(entries),
        "entries": entries,
    }


def server_metadata_json() -> str:
    """Metadata published through the server://info MCP resource."""
    return json.dumps(
        {
            "name": "log-inspector-mcp",
            "version": "2.0.0",
            "capabilities": [
                "log-search",
                "recent-error-discovery",
                "structured-log-search-v2",
                "bearer-token-auth-http",
            ],
            "tools": {
                "search_logs": {
                    "version": "1.0.0",
                    "deprecated": False,
                    "response": "list[str]",
                },
                "get_recent_errors": {
                    "version": "1.0.0",
                    "deprecated": False,
                    "response": "list[str]",
                },
                "search_logs_v2": {
                    "version": "2.0.0",
                    "deprecated": False,
                    "response": "structured JSON",
                    "replaces": "search_logs for clients that support v2",
                },
            },
            "backward_compatibility": (
                "search_logs v1 is kept unchanged; new clients may opt into "
                "search_logs_v2 after reading this resource"
            ),
        },
        ensure_ascii=False,
    )
