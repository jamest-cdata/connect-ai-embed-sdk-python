from __future__ import annotations

import csv
import io
import re

from .mcp_client import McpClient
from .types import ConnectAIError, QueryResult

_BLOCKED_SQL = re.compile(r"\b(DELETE|DROP|TRUNCATE|ALTER)\b", re.IGNORECASE)


class QueryClient:
    def __init__(self, mcp_client: McpClient, safety_sql: bool = True) -> None:
        self._mcp = mcp_client
        self._safety_sql = safety_sql

    async def execute(self, catalog: str, query: str) -> QueryResult:
        if self._safety_sql and _BLOCKED_SQL.search(query):
            raise ConnectAIError(
                "Query blocked by safety filter: destructive SQL detected"
            )

        result = await self._mcp.call_tool("queryData", {
            "catalogName": catalog,
            "query": query,
        })

        text_content = next(
            (c.text for c in result.content if c.type == "text" and c.text), None
        )
        if not text_content:
            return QueryResult(rows=[], headers=[])

        return self._parse_csv(text_content)

    @staticmethod
    def _parse_csv(text: str) -> QueryResult:
        reader = csv.DictReader(io.StringIO(text.strip()))
        headers = [h for h in (reader.fieldnames or []) if h is not None]
        rows = []
        for row in reader:
            rows.append({
                k: (v if v is not None else "")
                for k, v in row.items()
                if k is not None
            })
        return QueryResult(rows=rows, headers=headers)
