from __future__ import annotations

from typing import Any

import httpx

from .base import LLMProvider, LLMTurnResult, ToolCall, ToolDefinition, ToolResultEntry


class AnthropicProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int,
        temperature: float,
        base_url: str = "https://api.anthropic.com",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._base_url = base_url

    async def send_turn(
        self,
        system_prompt: str,
        messages: list[Any],
        tools: list[ToolDefinition],
    ) -> LLMTurnResult:
        anthropic_tools = [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in tools
        ]

        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{self._base_url}/v1/messages",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self._api_key,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": self._model,
                    "max_tokens": self._max_tokens,
                    "temperature": self._temperature,
                    "system": system_prompt,
                    "tools": anthropic_tools,
                    "messages": messages,
                },
                timeout=120.0,
            )

        if res.status_code != 200:
            raise RuntimeError(f"Anthropic API error: {res.status_code} {res.text[:500]}")

        body = res.json()
        text = ""
        tool_calls: list[ToolCall] = []

        for block in body.get("content", []):
            if block["type"] == "text":
                text += block["text"]
            elif block["type"] == "tool_use":
                tool_calls.append(ToolCall(id=block["id"], name=block["name"], args=block["input"]))

        return LLMTurnResult(
            text=text,
            tool_calls=tool_calls,
            done=body.get("stop_reason") != "tool_use" or len(tool_calls) == 0,
        )

    def format_assistant_message(self, text: str, tool_calls: list[ToolCall]) -> Any:
        content: list[Any] = []
        if text:
            content.append({"type": "text", "text": text})
        for tc in tool_calls:
            content.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.args})
        return {"role": "assistant", "content": content}

    def format_tool_results(self, results: list[ToolResultEntry]) -> Any:
        return {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": r.call_id, "content": r.result}
                for r in results
            ],
        }
