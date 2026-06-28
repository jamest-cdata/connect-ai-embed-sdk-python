from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from .auth import JwtBuilder
from .types import ConnectAIError


class MetadataClient:
    def __init__(self, query_url: str, jwt_builder: JwtBuilder) -> None:
        self._query_url = query_url
        self._jwt = jwt_builder

    def _headers(self, sub_account_id: str | None = None) -> dict[str, str]:
        token = self._jwt.build(sub_account_id)
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

    async def get_schemas(
        self, catalog_name: str, sub_account_id: str | None = None
    ) -> list[dict[str, Any]]:
        params = urlencode({"catalogName": catalog_name})
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.get(
                f"{self._query_url}/schemas?{params}",
                headers=self._headers(sub_account_id),
            )
        if res.status_code != 200:
            raise ConnectAIError(f"HTTP {res.status_code}", res.status_code)
        return res.json()

    async def get_tables(
        self,
        catalog_name: str,
        schema_name: str,
        sub_account_id: str | None = None,
    ) -> list[dict[str, Any]]:
        params = urlencode({"catalogName": catalog_name, "schemaName": schema_name})
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.get(
                f"{self._query_url}/tables?{params}",
                headers=self._headers(sub_account_id),
            )
        if res.status_code != 200:
            raise ConnectAIError(f"HTTP {res.status_code}", res.status_code)
        return res.json()

    async def get_columns(
        self,
        catalog_name: str,
        schema_name: str,
        table_name: str,
        sub_account_id: str | None = None,
    ) -> list[dict[str, Any]]:
        params = urlencode({
            "catalogName": catalog_name,
            "schemaName": schema_name,
            "tableName": table_name,
        })
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.get(
                f"{self._query_url}/columns?{params}",
                headers=self._headers(sub_account_id),
            )
        if res.status_code != 200:
            raise ConnectAIError(f"HTTP {res.status_code}", res.status_code)
        return res.json()
