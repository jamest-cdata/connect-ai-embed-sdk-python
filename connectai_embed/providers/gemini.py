from __future__ import annotations

from typing import Any

import httpx

from .base import LLMProvider, LLMTurnResult, ToolCall, ToolDefinition, ToolResultEntry


class GeminiProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int,
        temperature: float,
        base_url: str = "https://generativelanguage.googleapis.com",
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
        gemini_tools = [
            {
                "functionDeclarations": [
                    {
                        "name": t.name,
                        "description": t.description,
                        "parameters": self._to_gemini_schema(t.input_schema),
                    }
                    for t in tools
                ]
            }
        ]

        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{self._base_url}/v1beta/models/{self._model}:generateContent",
                params={"key": self._api_key},
                headers={"Content-Type": "application/json"},
                json={
                    "systemInstruction": {"parts": [{"text": system_prompt}]},
                    "contents": messages,
                    "tools": gemini_tools,
                    "generationConfig": {
                        "maxOutputTokens": self._max_tokens,
                        "temperature": self._temperature,
                    },
                },
                timeout=120.0,
            )

        if res.status_code != 200:
            raise RuntimeError(f"Gemini API error: {res.status_code} {res.text[:500]}")

        body = res.json()
        candidate = (body.get("candidates") or [{}])[0]

        text = ""
        tool_calls: list[ToolCall] = []
        call_counter = 0

        for part in candidate.get("content", {}).get("parts", []):
            if "text" in part:
                text += part["text"]
            elif "functionCall" in part:
                call_counter += 1
                fc = part["functionCall"]
                tool_calls.append(
                    ToolCall(
                        id=f"gemini_call_{call_counter}",
                        name=fc["name"],
                        args=fc.get("args", {}),
                    )
                )

        return LLMTurnResult(
            text=text,
            tool_calls=tool_calls,
            done=len(tool_calls) == 0,
        )

    def format_assistant_message(self, text: str, tool_calls: list[ToolCall]) -> Any:
        parts: list[Any] = []
        if text:
            parts.append({"text": text})
        for tc in tool_calls:
            parts.append({"functionCall": {"name": tc.name, "args": tc.args}})
        return {"role": "model", "parts": parts}

    def format_tool_results(self, results: list[ToolResultEntry]) -> Any:
        return {
            "role": "user",
            "parts": [
                {
                    "functionResponse": {
                        "name": r.name,
                        "response": {"result": r.result},
                    }
                }
                for r in results
            ],
        }

    @staticmethod
    def _to_gemini_schema(schema: dict[str, Any]) -> dict[str, Any]:
        copy = {k: v for k, v in schema.items() if k not in ("$schema", "additionalProperties")}
        return copy
