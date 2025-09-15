from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from aiogram import Bot
import aiosqlite

from shemas import DuePayload
from config import INTERNAL_TOKEN
from storage import store


router = APIRouter()

@router.get("/healthz")
async def healthz():
    return {"ok": True, "service": "bot"}


@router.post("/notify-due")
async def notify_due(p: DuePayload, authorization: str = Header("")):
    """
    Принимаем уведомление от backend Celery.
    Находим chat_id по user_id в локальном сторе и отправляем сообщение.
    В этом MVP мы храним связь chat_id <-> user_id/токены по chat_id, поэтому
    переберём записи (для простоты) — обычно у тебя будет отдельная таблица map user_id -> chat_id.
    """
    if authorization != f"Bearer {INTERNAL_TOKEN}":
        raise HTTPException(status_code=401, detail="unauthorized")

    
    async with aiosqlite.connect(store.db_path) as db:
        async with db.execute("SELECT chat_id FROM auth WHERE user_id = ?", (p.user_id,)) as cur:
            rows = await cur.fetchall()

    if not rows:
        # Пользователь ещё не логинился в бота — просто проглотим
        return {"ok": True, "delivered": False, "reason": "no chat bound"}

    text = (
        f"🕒 Напоминание о дедлайне\n"
        f"Задача: {p.title}\n"
        f"Время: {p.due_at or '—'}\n"
        f"(task_id={p.task_id})"
    )
    for (chat_id,) in rows:
        try:
            await bot.send_message(chat_id, text)
        except Exception:
            # не валим весь запрос, просто идём дальше
            pass
    return {"ok": True, "delivered": True, "chat_count": len(rows)}
