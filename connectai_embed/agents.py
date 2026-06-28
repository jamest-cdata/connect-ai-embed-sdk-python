from __future__ import annotations

import re
from typing import Any, Callable

from .mcp_client import McpClient
from .providers.base import LLMProvider, ToolDefinition, ToolResultEntry
from .providers.factory import create_provider
from .types import (
    AgentConfig,
    AgentResponse,
    AgentStreamEvent,
    ChatMessage,
    McpTool,
    ToolCallRecord,
)

_BLOCKED_SQL = re.compile(r"\b(DELETE|DROP|TRUNCATE|ALTER)\b", re.IGNORECASE)

_DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful data assistant powered by CData Connect AI. "
    "You have access to tools that can query databases, list schemas, tables, and columns. "
    "When the user asks a data question, use the available tools to find and return the answer. "
    "Always show results in a clear, formatted way."
)

_DEFAULT_DASHBOARD_PROMPT = (
    "You are a dashboard assistant powered by CData Connect AI. "
    "Help the user explore and visualize their data. Use the available tools to query data "
    "and provide insights. Return data in structured formats suitable for charts and tables."
)


class ChatAgent:
    def __init__(
        self,
        mcp_client: McpClient,
        config: AgentConfig | None = None,
        provider: LLMProvider | None = None,
    ) -> None:
        self._mcp = mcp_client
        self._config = config or AgentConfig()
        if not self._config.system_prompt:
            self._config.system_prompt = _DEFAULT_SYSTEM_PROMPT
        self._provider = provider or create_provider(self._config)
        self._tools: list[McpTool] = []
        self._tool_defs: list[ToolDefinition] = []
        self._messages: list[Any] = []
        self._history: list[ChatMessage] = []

    async def initialize(self) -> list[McpTool]:
        await self._mcp.initialize()
        self._tools = await self._mcp.list_tools()
        self._tool_defs = [
            ToolDefinition(
                name=t.name,
                description=t.description or "",
                input_schema=t.input_schema or {"type": "object", "properties": {}},
            )
            for t in self._tools
        ]
        return self._tools

    @property
    def tools(self) -> list[McpTool]:
        return self._tools

    def clear_history(self) -> None:
        self._messages.clear()
        self._history.clear()

    async def chat(
        self,
        message: str,
        on_stream: Callable[[AgentStreamEvent], None] | None = None,
    ) -> AgentResponse:
        self._history.append(ChatMessage(role="user", content=message))
        self._messages.append({"role": "user", "content": message})

        tool_call_records: list[ToolCallRecord] = []
        final_content = ""
        rounds = 0

        while rounds < self._config.max_tool_rounds:
            rounds += 1

            try:
                turn = await self._provider.send_turn(
                    self._config.system_prompt or "",
                    self._messages,
                    self._tool_defs,
                )
            except Exception as exc:
                if on_stream:
                    on_stream(AgentStreamEvent(type="error", error=str(exc)))
                raise

            if turn.text and on_stream:
                on_stream(AgentStreamEvent(type="text", content=turn.text))
            for tc in turn.tool_calls:
                if on_stream:
                    on_stream(AgentStreamEvent(
                        type="tool_use", tool_name=tc.name, tool_args=tc.args
                    ))

            if turn.done:
                final_content = turn.text
                break

            self._messages.append(
                self._provider.format_assistant_message(turn.text, turn.tool_calls)
            )

            tool_results: list[ToolResultEntry] = []

            for tc in turn.tool_calls:
                if (
                    self._config.safety_sql
                    and tc.name == "queryData"
                    and isinstance(tc.args.get("query"), str)
                    and _BLOCKED_SQL.search(tc.args["query"])
                ):
                    blocked = "Query blocked: destructive SQL is not allowed."
                    tool_results.append(ToolResultEntry(call_id=tc.id, name=tc.name, result=blocked))
                    if on_stream:
                        on_stream(AgentStreamEvent(
                            type="tool_result", tool_name=tc.name, tool_result=blocked
                        ))
                    tool_call_records.append(ToolCallRecord(
                        name=tc.name, args=tc.args, result=blocked
                    ))
                    continue

                try:
                    result = await self._mcp.call_tool(tc.name, tc.args)
                    result_text = "\n".join(c.text for c in result.content if c.text) or str(result)
                    tool_results.append(ToolResultEntry(
                        call_id=tc.id, name=tc.name, result=result_text
                    ))
                    if on_stream:
                        on_stream(AgentStreamEvent(
                            type="tool_result", tool_name=tc.name, tool_result=result_text
                        ))
                    tool_call_records.append(ToolCallRecord(
                        name=tc.name, args=tc.args, result=result_text
                    ))
                except Exception as exc:
                    err_msg = str(exc)
                    tool_results.append(ToolResultEntry(
                        call_id=tc.id, name=tc.name, result=f"Error: {err_msg}"
                    ))
                    if on_stream:
                        on_stream(AgentStreamEvent(
                            type="tool_result", tool_name=tc.name, tool_result=f"Error: {err_msg}"
                        ))
                    tool_call_records.append(ToolCallRecord(
                        name=tc.name, args=tc.args, result=f"Error: {err_msg}"
                    ))

            formatted = self._provider.format_tool_results(tool_results)
            if isinstance(formatted, list):
                self._messages.extend(formatted)
            else:
                self._messages.append(formatted)

        self._history.append(ChatMessage(role="assistant", content=final_content))
        if on_stream:
            on_stream(AgentStreamEvent(type="done", content=final_content))

        return AgentResponse(
            content=final_content,
            tool_calls=tool_call_records if tool_call_records else None,
        )


class DashboardAgent(ChatAgent):
    def __init__(
        self,
        mcp_client: McpClient,
        config: AgentConfig | None = None,
        provider: LLMProvider | None = None,
    ) -> None:
        cfg = config or AgentConfig()
        if not cfg.system_prompt:
            cfg.system_prompt = _DEFAULT_DASHBOARD_PROMPT
        cfg.max_tool_rounds = min(cfg.max_tool_rounds, 5)
        super().__init__(mcp_client, cfg, provider)
