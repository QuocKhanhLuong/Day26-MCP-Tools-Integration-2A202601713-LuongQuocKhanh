from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp.client.client import Client  # noqa: E402
from server_stdio import mcp  # noqa: E402


class MCPContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_tool_discovery_and_real_call(self) -> None:
        async with Client(mcp) as client:
            tools = await client.list_tools()
            names = {tool.name for tool in tools.tools}
            self.assertIn("search_logs", names)
            self.assertIn("get_recent_errors", names)
            self.assertIn("search_logs_v2", names)

            result = await client.call_tool(
                "get_recent_errors", {"log_file": "sample.log", "limit": 2}
            )
            text = "\n".join(
                item.text for item in result.content if hasattr(item, "text")
            )
            self.assertIn("ERROR", text)

    async def test_server_info_resource_is_readable(self) -> None:
        async with Client(mcp) as client:
            info = await client.read_resource("server://info")
            metadata = json.loads(info.contents[0].text)
            self.assertEqual(metadata["version"], "2.0.0")
            self.assertIn("search_logs_v2", metadata["tools"])


if __name__ == "__main__":
    unittest.main()
