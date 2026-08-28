"""Capability-aware HTTP client that reads server://info before choosing a tool."""

from __future__ import annotations

import asyncio
import json
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

                info = await session.read_resource("server://info")
                metadata = json.loads(info.contents[0].text)
                tools = metadata.get("tools", {})

                print(
                    f"Server {metadata.get('name')} v{metadata.get('version')} "
                    f"capabilities={metadata.get('capabilities')}"
                )

                if "search_logs_v2" in tools:
                    tool_name = "search_logs_v2"
                else:
                    tool_name = "search_logs"

                result = await session.call_tool(
                    tool_name,
                    {"keyword": "ERROR", "log_file": "sample.log", "limit": 5},
                )
                print(f"Selected tool: {tool_name}")
                for item in result.content:
                    print(item.text)


if __name__ == "__main__":
    asyncio.run(main())
