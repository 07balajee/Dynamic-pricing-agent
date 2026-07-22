"""Thin MCP client wrapper so callers don't deal with session/stdio boilerplate.

Spawns mcp_server/signals_server.py as a subprocess over stdio per call. Fine for a
learning project / low request volume; a long-lived session would be the next
optimization if this were a real production path.
"""
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class SignalsClient:
    def __init__(self):
        self._params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server.signals_server"],
            cwd=str(_PROJECT_ROOT),
        )

    async def _call_tool(self, tool_name: str, arguments: dict):
        async with stdio_client(self._params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                if result.isError:
                    raise RuntimeError(f"MCP tool '{tool_name}' failed: {result.content}")
                return result.content[0].text

    async def get_weather(self, city: str, api_key: str) -> str:
        return await self._call_tool("get_weather", {"city": city, "api_key": api_key})

    async def get_vendor_price(
        self,
        base_price: float,
        inventory_stock: int,
        competitor_price: float,
        expiry_date: str,
    ) -> float:
        result = await self._call_tool(
            "get_vendor_price",
            {
                "base_price": base_price,
                "inventory_stock": inventory_stock,
                "competitor_price": competitor_price,
                "expiry_date": expiry_date,
            },
        )
        return float(result)
