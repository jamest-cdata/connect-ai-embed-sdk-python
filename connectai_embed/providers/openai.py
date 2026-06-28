from __future__ import annotations

import json
from typing import Any

import httpx

from .base import LLMProvider, LLMTurnResult, ToolCall, ToolDefinition, ToolResultEntry


class OpenAIProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int,
        temperature: float,
        base_url: str = "https://api.openai.com",
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
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            }
            for t in tools
        ]

        all_messages = [{"role": "system", "content": system_prompt}, *messages]

        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{self._base_url}/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._api_key}",
                },
                json={
                    "model": self._model,
                    "max_tokens": self._max_tokens,
                    "temperature": self._temperature,
                    "tools": openai_tools,
                    "messages": all_messages,
                },
                timeout=120.0,
            )

        if res.status_code != 200:
            raise RuntimeError(f"OpenAI API error: {res.status_code} {res.text[:500]}")

        body = res.json()
        choice = body.get("choices", [{}])[0]
        message = choice.get("message", {})

        text = message.get("content") or ""
        tool_calls = [
            ToolCall(
                id=tc["id"],
                name=tc["function"]["name"],
                args=json.loads(tc["function"]["arguments"]),
            )
            for tc in message.get("tool_calls", [])
        ]

        return LLMTurnResult(
            text=text,
            tool_calls=tool_calls,
            done=choice.get("finish_reason") != "tool_calls" or len(tool_calls) == 0,
        )

    def format_assistant_message(self, text: str, tool_calls: list[ToolCall]) -> Any:
        return {
            "role": "assistant",
            "content": text or None,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": json.dumps(tc.args)},
                }
                for tc in tool_calls
            ],
        }

    def format_tool_results(self, results: list[ToolResultEntry]) -> list[Any]:
        return [
            {"role": "tool", "tool_call_id": r.call_id, "content": r.result}
            for r in results
        ]
