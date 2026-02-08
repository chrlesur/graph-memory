# -*- coding: utf-8 -*-
"""
MCPClient - Communication avec le serveur MCP Memory.

Deux modes de communication :
  - REST : pour les endpoints simples (health, list, graph)
  - SSE/MCP : pour appeler les outils MCP (ingest, delete, search...)
"""

import json
from typing import Dict, Any


class MCPClient:
    """Client pour communiquer avec le serveur MCP Memory."""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token

    # =========================================================================
    # Transport bas niveau
    # =========================================================================

    async def _fetch(self, endpoint: str) -> dict:
        """Requête GET sur l'API REST."""
        import aiohttp

        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self.token}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                text = await response.text()
                raise Exception(f"HTTP {response.status}: {text}")

    async def call_tool(self, tool_name: str, args: dict) -> dict:
        """Appeler un outil MCP via le protocole SSE."""
        from mcp import ClientSession
        from mcp.client.sse import sse_client

        headers = {"Authorization": f"Bearer {self.token}"}

        async with sse_client(f"{self.base_url}/sse", headers=headers) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, args)
                return json.loads(result.content[0].text)

    # =========================================================================
    # Raccourcis API REST
    # =========================================================================

    async def list_memories(self) -> dict:
        """Liste les mémoires via REST."""
        return await self._fetch("/api/memories")

    async def get_graph(self, memory_id: str) -> dict:
        """Récupère le graphe complet d'une mémoire via REST."""
        return await self._fetch(f"/api/graph/{memory_id}")
