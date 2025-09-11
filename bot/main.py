import os

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

@app.get("/internal/healthz")
async def healthz():
    return {"ok": True, "service": "bot"}

# Заглушка под будущий эндпойнт уведомлений:
class DuePayload(BaseModel):
    user_id: int
    task_id: int
    title: str
    due_at: str | None = None

@app.post("/internal/notify-due")
async def notify_due(_: DuePayload):
    # позже тут будет отправка в Telegram
    return {"accepted": True}
