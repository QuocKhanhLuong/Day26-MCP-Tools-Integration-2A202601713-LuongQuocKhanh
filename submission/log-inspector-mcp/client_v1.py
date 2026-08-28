"""Legacy HTTP client: calls the v1 tool without reading server metadata."""

from __future__ import annotations

import asyncio
import os

import httpx2
from mcp.client.client import Client
from mcp.client.streamable_http import streamable_http_client

SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp")


async def main() -> None:
    token = os.getenv("MCP_AUTH_TOKEN")
    if not token:
        raise SystemExit("Set MCP_AUTH_TOKEN before running this client.")

    timeout = httpx2.Timeout(30.0, read=300.0)
    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
        timeout=timeout,
        follow_redirects=True,
    ) as http_client:
        transport = streamable_http_client(SERVER_URL, http_client=http_client)
        async with Client(transport) as client:
            result = await client.call_tool(
                "search_logs",
                {"keyword": "ERROR", "log_file": "sample.log", "limit": 5},
            )
            print("Legacy v1 result:")
            for item in result.content:
                if hasattr(item, "text"):
                    print(item.text)
                else:
                    print(item)


if __name__ == "__main__":
    asyncio.run(main())
