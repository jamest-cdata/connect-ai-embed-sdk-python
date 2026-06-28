from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]


@dataclass
class LLMTurnResult:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    done: bool = True


@dataclass
class ToolResultEntry:
    call_id: str
    name: str
    result: str


class LLMProvider(ABC):
    @abstractmethod
    async def send_turn(
        self,
        system_prompt: str,
        messages: list[Any],
        tools: list[ToolDefinition],
    ) -> LLMTurnResult: ...

    @abstractmethod
    def format_assistant_message(self, text: str, tool_calls: list[ToolCall]) -> Any: ...

    @abstractmethod
    def format_tool_results(self, results: list[ToolResultEntry]) -> Any: ...
