from __future__ import annotations

from .accounts import AccountsClient
from .agents import ChatAgent, DashboardAgent
from .auth import JwtBuilder
from .connections import ConnectionsClient
from .metadata import MetadataClient
from .mcp_client import McpClient
from .queries import QueryClient
from .types import AgentConfig, ConnectAIEmbedConfig


class ConnectAIEmbedClient:
    def __init__(self, config: ConnectAIEmbedConfig) -> None:
        self._config = config
        self._jwt_builder = JwtBuilder(
            config.account_id,
            config.private_key,
            config.jwt_expires_in,
        )
        self.accounts = AccountsClient(config.base_url, self._jwt_builder)
        self.connections = ConnectionsClient(config.base_url, self._jwt_builder)
        self.metadata = MetadataClient(config.query_url, self._jwt_builder)

    def build_jwt(self, sub_account_id: str | None = None) -> str:
        return self._jwt_builder.build(sub_account_id)

    def create_mcp_client(self, sub_account_id: str | None = None) -> McpClient:
        token = self._jwt_builder.build(sub_account_id)
        refresher = self._jwt_builder.build_refresher(sub_account_id)
        return McpClient(self._config.mcp_url, token, refresher)

    def create_query_client(
        self, sub_account_id: str | None = None, safety_sql: bool = True
    ) -> QueryClient:
        mcp = self.create_mcp_client(sub_account_id)
        return QueryClient(mcp, safety_sql)

    def create_chat_agent(
        self, sub_account_id: str | None = None, config: AgentConfig | None = None
    ) -> ChatAgent:
        mcp = self.create_mcp_client(sub_account_id)
        return ChatAgent(mcp, config)

    def create_dashboard_agent(
        self, sub_account_id: str | None = None, config: AgentConfig | None = None
    ) -> DashboardAgent:
        mcp = self.create_mcp_client(sub_account_id)
        return DashboardAgent(mcp, config)
