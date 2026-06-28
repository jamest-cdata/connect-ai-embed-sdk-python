from __future__ import annotations

import time
from typing import Callable

import jwt


class JwtBuilder:
    def __init__(self, account_id: str, private_key: str, default_expiry: str = "3 minutes"):
        self._account_id = account_id
        self._private_key = private_key
        self._default_expiry_seconds = self._parse_expiry(default_expiry)

    @staticmethod
    def _parse_expiry(expiry: str) -> int:
        parts = expiry.strip().split()
        if len(parts) == 2:
            value, unit = int(parts[0]), parts[1].lower()
            if unit.startswith("minute"):
                return value * 60
            if unit.startswith("hour"):
                return value * 3600
            if unit.startswith("second"):
                return value
        return 180  # default 3 minutes

    def build(self, sub_account_id: str | None = None, expires_in: str | None = None) -> str:
        now = int(time.time())
        ttl = self._parse_expiry(expires_in) if expires_in else self._default_expiry_seconds

        payload: dict = {
            "tokenType": "powered-by",
            "iss": self._account_id,
            "iat": now,
            "exp": now + ttl,
        }
        if sub_account_id:
            payload["sub"] = sub_account_id

        return jwt.encode(payload, self._private_key, algorithm="RS256")

    def build_refresher(self, sub_account_id: str | None = None) -> Callable[[], str]:
        def _refresh() -> str:
            return self.build(sub_account_id)
        return _refresh
