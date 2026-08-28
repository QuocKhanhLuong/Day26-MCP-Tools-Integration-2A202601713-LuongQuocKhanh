"""Legacy HTTP client: calls the v1 tool without reading server metadata."""

from __future__ import annotations

import asyncio
import os

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")


async def main() -> None:
    token = os.getenv("MCP_AUTH_TOKEN")
    if not token:
        raise SystemExit("Set MCP_AUTH_TOKEN before running this client.")

    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {token}"}
    ) as http_client:
        async with streamable_http_client(
            SERVER_URL, http_client=http_client
        ) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "search_logs",
                    {"keyword": "ERROR", "log_file": "sample.log", "limit": 5},
                )
                print("Legacy v1 result:")
                for item in result.content:
                    print(item.text)


if __name__ == "__main__":
    asyncio.run(main())
