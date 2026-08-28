"""Capability-aware HTTP client that reads server://info before choosing a tool."""

from __future__ import annotations

import asyncio
import json
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
            info = await client.read_resource("server://info")
            metadata = json.loads(info.contents[0].text)
            tools = metadata.get("tools", {})

            print(
                f"Server {metadata.get('name')} v{metadata.get('version')} "
                f"capabilities={metadata.get('capabilities')}"
            )

            tool_name = "search_logs_v2" if "search_logs_v2" in tools else "search_logs"
            result = await client.call_tool(
                tool_name,
                {"keyword": "ERROR", "log_file": "sample.log", "limit": 5},
            )
            print(f"Selected tool: {tool_name}")
            for item in result.content:
                if hasattr(item, "text"):
                    print(item.text)
                else:
                    print(item)


if __name__ == "__main__":
    asyncio.run(main())
