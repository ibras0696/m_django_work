# bot/main.py
import contextlib
import os
import asyncio
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

from storage import store
from config import TELEGRAM_TOKEN
from handlers import router
from routes import router as routes_router

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN env is required")

bot = Bot(token=TELEGRAM_TOKEN)

dp = Dispatcher()

dp.include_router(router)

app = FastAPI()
app.include_router(routes_router)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Инициализация sqlite
    await store.init()
    # Стартуем aiogram polling в фоне
    loop = asyncio.get_event_loop()
    # Делаем bot доступным маршрутам через app.state
    app.state.bot = bot
    polling_task = loop.create_task(dp.start_polling(bot))
    try:
        yield
    finally:
        polling_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await polling_task
        await bot.session.close()


# Привязываем lifespan к FastAPI
app.router.lifespan_context = lifespan
