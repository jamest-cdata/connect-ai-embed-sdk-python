from __future__ import annotations

from typing import Any, Callable, Literal

from pydantic import BaseModel, Field


# ─── Client Configuration ────────────────────────────────────────────────────


class ConnectAIEmbedConfig(BaseModel):
    account_id: str
    private_key: str
    base_url: str = "https://cloud.cdata.com"
    query_url: str = "https://cloud.cdata.com/api"
    mcp_url: str = "https://mcp.cloud.cdata.com/mcp"
    jwt_expires_in: str = "3 minutes"


# ─── Connections ──────────────────────────────────────────────────────────────


class DataSource(BaseModel, extra="allow"):
    name: str
    display_name: str | None = None


class Connection(BaseModel, extra="allow"):
    id: str
    name: str
    data_source: str = Field(alias="dataSource")
    last_modified: str | None = Field(None, alias="lastModified")


class CreateConnectionOptions(BaseModel):
    driver: str
    redirect_url: str
    connection_name: str | None = None


class UpdateConnectionOptions(BaseModel):
    connection_id: str
    redirect_url: str


class ConnectionUrlResponse(BaseModel):
    redirect_url: str = Field(alias="redirectURL")


# ─── Metadata ─────────────────────────────────────────────────────────────────


class Schema(BaseModel, extra="allow"):
    schema_name: str = Field(alias="schemaName")


class Table(BaseModel, extra="allow"):
    table_name: str = Field(alias="tableName")
    table_type: str | None = Field(None, alias="tableType")


class Column(BaseModel, extra="allow"):
    column_name: str = Field(alias="columnName")
    data_type: str | None = Field(None, alias="dataType")
    is_nullable: bool | None = Field(None, alias="isNullable")


# ─── MCP ──────────────────────────────────────────────────────────────────────


class McpTool(BaseModel, extra="allow"):
    name: str
    description: str | None = None
    input_schema: dict[str, Any] | None = Field(None, alias="inputSchema")


class McpToolResultContent(BaseModel, extra="allow"):
    type: str
    text: str | None = None
    data: str | None = None
    mime_type: str | None = Field(None, alias="mimeType")


class McpToolResult(BaseModel, extra="allow"):
    content: list[McpToolResultContent] = []
    is_error: bool | None = Field(None, alias="isError")


# ─── Queries ──────────────────────────────────────────────────────────────────


class QueryResult(BaseModel, extra="allow"):
    rows: list[dict[str, Any]] = []
    headers: list[str] | None = None


# ─── Agents ───────────────────────────────────────────────────────────────────


class AgentConfig(BaseModel):
    provider: Literal["anthropic", "openai", "gemini"] | None = None
    api_key: str | None = None
    api_base_url: str | None = None
    model: str | None = None
    system_prompt: str | None = None
    max_tool_rounds: int = 10
    temperature: float = 0
    max_tokens: int = 4096
    safety_sql: bool = True


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AgentStreamEvent(BaseModel):
    type: Literal["text", "tool_use", "tool_result", "done", "error"]
    content: str | None = None
    tool_name: str | None = None
    tool_args: dict[str, Any] | None = None
    tool_result: str | None = None
    error: str | None = None


class ToolCallRecord(BaseModel):
    name: str
    args: dict[str, Any]
    result: str


class AgentResponse(BaseModel):
    content: str
    tool_calls: list[ToolCallRecord] | None = None


# ─── Errors ───────────────────────────────────────────────────────────────────


class ConnectAIError(Exception):
    def __init__(self, message: str, status_code: int | None = None, response: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response
