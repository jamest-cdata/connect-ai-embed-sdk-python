from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from .auth import JwtBuilder
from .types import ConnectAIError


class AccountsClient:
    def __init__(self, base_url: str, jwt_builder: JwtBuilder) -> None:
        self._base_url = base_url
        self._jwt = jwt_builder

    def _headers(self, sub_account_id: str | None = None) -> dict[str, str]:
        token = self._jwt.build(sub_account_id)
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

    async def create(
        self,
        external_id: str,
        account_name: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, str] = {"externalId": external_id}
        if account_name:
            body["accountname"] = account_name

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(
                f"{self._base_url}/api/poweredby/account/create",
                headers=self._headers(),
                json=body,
            )
        if res.status_code != 200:
            raise ConnectAIError(f"HTTP {res.status_code}", res.status_code, res.json())

        create_response = res.json()

        # The create endpoint doesn't return the CData UUID directly.
        # Fetch the account by externalId to get the system-generated id.
        account = await self.get(external_id)
        if account:
            create_response["id"] = account.get("id") or account.get("accountId")
        return create_response

    async def list(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.get(
                f"{self._base_url}/api/poweredby/account/list",
                headers=self._headers(),
            )
        if res.status_code != 200:
            raise ConnectAIError(f"HTTP {res.status_code}", res.status_code, res.json())
        return res.json()

    async def get(self, external_id: str) -> dict[str, Any] | None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.get(
                f"{self._base_url}/api/poweredby/account/{quote(external_id)}",
                headers=self._headers(),
            )
        if res.status_code == 404:
            return None
        if res.status_code != 200:
            raise ConnectAIError(f"HTTP {res.status_code}", res.status_code, res.json())
        return res.json()

    async def delete(self, sub_account_id: str) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.request(
                "DELETE",
                f"{self._base_url}/api/poweredby/account/delete/{quote(sub_account_id)}",
                headers=self._headers(),
                json={},
            )
        if res.status_code >= 400:
            raise ConnectAIError(f"HTTP {res.status_code}", res.status_code, res.json())

    async def get_data_explorer_url(
        self,
        sub_account_id: str,
        redirect_url: str | None = None,
    ) -> dict[str, str]:
        body: dict[str, str] = {}
        if redirect_url:
            body["redirectURL"] = redirect_url

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(
                f"{self._base_url}/api/poweredby/dataExplorer",
                headers=self._headers(sub_account_id),
                json=body,
            )
        if res.status_code != 200:
            raise ConnectAIError(f"HTTP {res.status_code}", res.status_code, res.json())
        return res.json()
