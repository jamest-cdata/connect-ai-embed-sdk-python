from __future__ import annotations

from typing import Any

import httpx

from .auth import JwtBuilder
from .types import (
    Connection,
    ConnectionUrlResponse,
    ConnectAIError,
    CreateConnectionOptions,
    DataSource,
    UpdateConnectionOptions,
)


class ConnectionsClient:
    def __init__(self, base_url: str, jwt_builder: JwtBuilder) -> None:
        self._base_url = base_url
        self._jwt = jwt_builder

    def _headers(self, sub_account_id: str | None = None) -> dict[str, str]:
        token = self._jwt.build(sub_account_id)
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

    async def list_sources(self, sub_account_id: str | None = None) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.get(
                f"{self._base_url}/api/poweredby/sources/list",
                headers=self._headers(sub_account_id),
            )
        if res.status_code != 200:
            raise ConnectAIError(f"HTTP {res.status_code}", res.status_code, res.json())
        data = res.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("sources") or data.get("dataSources") or [data]
        return [data]

    async def list_connections(self, sub_account_id: str | None = None) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.get(
                f"{self._base_url}/api/poweredby/connection/list",
                headers=self._headers(sub_account_id),
            )
        if res.status_code != 200:
            raise ConnectAIError(f"HTTP {res.status_code}", res.status_code, res.json())
        data = res.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("connections", "items", "value"):
                if key in data and isinstance(data[key], list):
                    return data[key]
            return [data]
        return [data]

    async def get_create_url(
        self,
        options: CreateConnectionOptions,
        sub_account_id: str | None = None,
    ) -> ConnectionUrlResponse:
        body: dict[str, str] = {
            "dataSource": options.driver,
            "redirectUrl": options.redirect_url,
        }
        if options.connection_name:
            body["name"] = options.connection_name.replace(" ", "-")

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(
                f"{self._base_url}/api/poweredby/connection/create",
                headers=self._headers(sub_account_id),
                json=body,
            )
        if res.status_code != 200:
            raise ConnectAIError(f"HTTP {res.status_code}", res.status_code, res.json())
        return ConnectionUrlResponse(**res.json())

    async def get_update_url(
        self,
        options: UpdateConnectionOptions,
        sub_account_id: str | None = None,
    ) -> ConnectionUrlResponse:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(
                f"{self._base_url}/api/poweredby/connection/edit/{options.connection_id}",
                headers=self._headers(sub_account_id),
                json={"redirectUrl": options.redirect_url},
            )
        if res.status_code != 200:
            raise ConnectAIError(f"HTTP {res.status_code}", res.status_code, res.json())
        return ConnectionUrlResponse(**res.json())
