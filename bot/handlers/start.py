from aiogram import Bot, Router, types
from aiogram.filters import Command

from service.django_api import api
from storage import store

router = Router()


@router.message(Command("start"))
async def on_start(message: types.Message):
    """
    Приветствие и краткая подсказка.
    Пользователь ещё не авторизован → предложим /login <username> <password>
    """
    await message.answer(
        "Ассаламу алейкум! Я бот ToDo.\n"
        "Авторизуйся: /login <username> <password>\n"
        "После входа: /tasks — показать твои задачи."
    )


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


@router.message(Command("tasks"))
async def on_tasks(message: types.Message):
    """
    Получить список задач из Django API с текущим access токеном.
    """
    auth = await store.get_auth(message.chat.id)
    if not auth:
        await message.answer("Сначала авторизуйся: /login <username> <password>")
        return
    user_id, access, refresh = auth

    try:
        items = api.list_tasks(access)
        if not items:
            await message.answer("Задач нет.")
            return

        text_lines = ["Твои задачи:"]
        for t in items[:20]:  # ограничим вывод
            cats = ", ".join(c["name"] for c in t.get("categories", [])) or "—"
            text_lines.append(
                f"• [{t['id']}] {t['title']} [{t['status']}]\n"
                f"  Категории: {cats}\n"
                f"  Создано: {t['created_at']}\n"
                f"  Дедлайн: {t.get('due_at') or '—'}"
            )
        await message.answer("\n".join(text_lines))
    except Exception as e:
        await message.answer(f"Ошибка запроса задач: {e!s}")

