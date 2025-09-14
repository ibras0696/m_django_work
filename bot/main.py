import os
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

INTERNAL_TOKEN = os.getenv("INTERNAL_TOKEN", "supersecret")

app = FastAPI()

@app.get("/internal/healthz")
async def healthz():
    return {"ok": True, "service": "bot"}

class DuePayload(BaseModel):
    user_id: int
    task_id: int
    title: str
    due_at: str | None = None

@app.post("/internal/notify-due")
async def notify_due(p: DuePayload, authorization: str = Header("")):
    """
    В реале тут вы бы нашли chat_id по user_id и вызвали aiogram Bot.
    Для смока — просто логируем/печатаем.
    """
    if authorization != f"Bearer {INTERNAL_TOKEN}":
        raise HTTPException(status_code=401, detail="unauthorized")

    print(f"[BOT] Notify user_id={p.user_id} task_id={p.task_id} title={p.title} due_at={p.due_at}")
    # TODO: aiogram send_message(chat_id, ...)
    return {"ok": True, "delivered": True}
