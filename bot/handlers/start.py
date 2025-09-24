from aiogram import Bot, Router, types
from aiogram.filters import Command

from service.django_api import api
from storage import store
from config import INTERNAL_TOKEN

router = Router()


@router.message(Command("start"))
async def on_start(message: types.Message):
    """
    Авторизуем пользователя в бэкенде по его Telegram-данным.
    """
    try:
        user = message.from_user
        payload = {
            "telegram_user_id": user.id,
            "chat_id": message.chat.id,
            "username": user.username or "",
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
        }
        res = api.bot_auth(payload, INTERNAL_TOKEN)
        access, refresh = res["access"], res["refresh"]
        user_id = int(res["user"]["id"])
        await store.upsert_tokens(message.chat.id, user_id, access, refresh)
        await message.answer(
            f"Готово. Связал тебя с аккаунтом Django (user_id={user_id}).\n"
            f"Команды: /tasks — список задач, скоро добавим добавление."
        )
    except Exception as e:
        await message.answer(f"Ошибка авторизации через бота: {e!s}\nПопробуй позже.")


@router.message(Command("login"))
async def on_login(message: types.Message):
    """
    /login username password
    Получаем JWT, узнаём user_id через /api/v1/me, связываем chat_id <-> user_id.
    """
    parts = message.text.strip().split(maxsplit=2)
    if len(parts) != 3:
        await message.answer("Используй: /login <username> <password>")
        return
    username, password = parts[1], parts[2]

    try:
        tokens = api.get_tokens(username, password)
        access, refresh = tokens["access"], tokens["refresh"]
        me = api.me(access)
        user_id = int(me["id"])
        await store.upsert_tokens(message.chat.id, user_id, access, refresh)
        await message.answer(f"Готово. Вошли как {me['username']} (user_id={user_id}). Теперь /tasks.")
    except Exception as e:
        await message.answer(f"Ошибка входа: {e!s}")

