from typing import Any

from storage import store
from service import api
from config import INTERNAL_TOKEN


async def ensure_auth(chat_id: int, user: Any) -> None:
    """Ensure chat has valid tokens in local store; if missing, perform bot_auth and persist.

    This is useful after bot restarts when SQLite store may be empty.
    """
    auth = await store.get_auth(chat_id)
    if auth:
        return
    payload = {
        "telegram_user_id": getattr(user, "id", None),
        "chat_id": chat_id,
        "username": getattr(user, "username", "") or "",
        "first_name": getattr(user, "first_name", "") or "",
        "last_name": getattr(user, "last_name", "") or "",
    }
    res = api.bot_auth(payload, INTERNAL_TOKEN)
    access, refresh = res["access"], res["refresh"]
    user_id = int(res["user"]["id"])
    await store.upsert_tokens(chat_id, user_id, access, refresh)

__all__ = ["ensure_auth"]
