# bot/django_api.py
import os
import httpx
from typing import Any

DJANGO_API_BASE = os.getenv("DJANGO_API_BASE", "http://backend:8000")

class DjangoAPI:
    def __init__(self, base: str = DJANGO_API_BASE):
        self.base = base.rstrip("/")

    def _url(self, path: str) -> str:
        return f"{self.base}{path}"

    def get_tokens(self, username: str, password: str) -> dict[str, Any]:
        """Получить JWT по username/password (dev-вариант)."""
        r = httpx.post(self._url("/api/token/"), json={"username": username, "password": password}, timeout=5.0)
        r.raise_for_status()
        return r.json()

    def me(self, access: str) -> dict[str, Any]:
        r = httpx.get(self._url("/api/v1/me"), headers={"Authorization": f"Bearer {access}"}, timeout=5.0)
        r.raise_for_status()
        return r.json()

    def list_tasks(self, access: str) -> list[dict[str, Any]]:
        r = httpx.get(self._url("/api/v1/tasks/"), headers={"Authorization": f"Bearer {access}"}, timeout=5.0)
        r.raise_for_status()
        return r.json()

        
api = DjangoAPI()