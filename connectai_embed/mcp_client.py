from __future__ import annotations

import json
import re
import time
from typing import Any, Callable

import httpx

from .types import ConnectAIError, McpTool, McpToolResult

_TOKEN_REFRESH_THRESHOLD_S = 120  # 2 minutes
_AUTH_ERROR_RE = re.compile(r"token|expired|unauthorized|auth", re.IGNORECASE)
_SSE_DATA_RE = re.compile(r"data: ({.*})")


class McpClient:
    def __init__(
        self,
        url: str,
        initial_token: str,
        token_refresher: Callable[[], str] | None = None,
    ) -> None:
        self._url = url
        self._token = initial_token
        self._token_refresher = token_refresher
        self._token_created_at = time.monotonic()
        self._message_id = 0

    def _refresh_token(self) -> None:
        if not self._token_refresher:
            return
        self._token = self._token_refresher()
        self._token_created_at = time.monotonic()

    def _ensure_fresh_token(self) -> None:
        if time.monotonic() - self._token_created_at > _TOKEN_REFRESH_THRESHOLD_S:
            self._refresh_token()

    async def _send_request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        retry_on_auth: bool = True,
    ) -> Any:
        self._message_id += 1
        body = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self._message_id,
        }

        async with httpx.AsyncClient() as client:
            res = await client.post(
                self._url,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
                json=body,
                timeout=60.0,
            )

        if res.status_code in (401, 403) and retry_on_auth and self._token_refresher:
            self._refresh_token()
            return await self._send_request(method, params, retry_on_auth=False)

        if res.status_code >= 400:
            raise ConnectAIError(f"MCP request failed: {res.status_code}", res.status_code)

        text = res.text
        match = _SSE_DATA_RE.search(text)
        if not match:
            raise ConnectAIError("Invalid MCP response format")

        data = json.loads(match.group(1))
        if "error" in data and data["error"]:
            err_msg = data["error"].get("message", json.dumps(data["error"]))
            if retry_on_auth and self._token_refresher and _AUTH_ERROR_RE.search(err_msg):
                self._refresh_token()
                return await self._send_request(method, params, retry_on_auth=False)
            raise ConnectAIError(f"MCP error: {err_msg}")

        return data.get("result")

    async def initialize(self) -> Any:
        return await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "connectai-embed-sdk-python", "version": "1.0.0"},
        })

    async def list_tools(self) -> list[McpTool]:
        result = await self._send_request("tools/list", {})
        tools_raw = result.get("tools", []) if isinstance(result, dict) else []
        return [McpTool(**t) for t in tools_raw]

    async def call_tool(self, name: str, args: dict[str, Any]) -> McpToolResult:
        self._ensure_fresh_token()
        result = await self._send_request("tools/call", {"name": name, "arguments": args})
        return McpToolResult(**result) if isinstance(result, dict) else McpToolResult(content=[])
