import contextlib

from aiogram.fsm.context import FSMContext
from aiogram import Router
from aiogram import types
from aiogram.filters import Command

from utils import parse_due
from service.django_api import with_auto_refresh

from states.task import AddTask
from service import api
from storage import store

router = Router()


@router.message(Command("add"))
async def add_start(message: types.Message, state: FSMContext):
    """
    Начинаем диалог добавления задачи.
    """
    await state.set_state(AddTask.waiting_title)
    await message.answer("Введи заголовок задачи:")


@router.message(AddTask.waiting_title)
async def add_got_title(message: types.Message, state: FSMContext):
    """
    Получили заголовок, спрашиваем дедлайн.
    """
    title = message.text.strip()
    # Простая валидация
    if not title:
        await message.answer("Заголовок не может быть пустым. Введи ещё раз:")
        return

    await state.update_data(title=title)
    await state.set_state(AddTask.waiting_due)
    await message.answer(
        "Ок. Теперь дедлайн (ISO с оффсетом, например `2025-09-15T12:30:00-09:00`)\n"
        "или коротко: `in 10m`, `in 2h`, `today 20:00`, `tomorrow 14:30`.\n"
        "Если без дедлайна — напиши `skip`."
    )


@router.message(AddTask.waiting_due)
async def add_got_due(message: types.Message, state: FSMContext):
    """
    Получили дедлайн, создаём задачу.
    """
    raw = message.text.strip()
    due = None
    if raw.lower() != "skip":
        # Парсим дату
        due = parse_due(raw)
        if not due:
            await message.answer("Не понял дату. Попробуй снова (ISO с оффсетом или `in 10m`/`today 20:00`).")
            return

    data = await state.get_data()
    title = data["title"]

    # Собираем payload для API
    payload = {"title": title}
    if due:
        payload["due_at"] = due.isoformat()

    # Вызываем backend с авто-refresh токена
    try:
        # Получаем результат
        result = await with_auto_refresh(
            message.chat.id,
            store,
            lambda access: api.create_task(access, payload),
            lambda refresh: api.refresh(refresh),
        )
        await message.answer(
            f"Создано ✅\n[id={result['id']}] {result['title']}\nДедлайн: {result.get('due_at') or '—'}")
    except Exception as e:
        await message.answer(f"Ошибка создания: {e!s}")

    await state.clear()


@router.message(Command("tasks"))
async def on_tasks(message: types.Message):
    """
    Показать список задач.
    """
    try:
        # Получаем список задач
        items = await with_auto_refresh(
            message.chat.id,
            store,
            lambda access: api.list_tasks(access),
            lambda refresh: api.refresh(refresh),
        )
    except Exception as e:
        await message.answer(f"Нужно авторизоваться: /start (ошибка: {e!s})")
        return

    if not items:
        await message.answer("Задач нет.")
        return

    text_lines = ["Твои задачи:"]
    for t in items[:20]:
        cats = ", ".join(c["name"] for c in t.get("categories", [])) or "—"
        text_lines.append(
            f"• [{t['id']}] {t['title']} [{t['status']}]\n"
            f"  Категории: {cats}\n"
            f"  Создано: {t['created_at']}\n"
            f"  Дедлайн: {t.get('due_at') or '—'}"
        )
    await message.answer("\n".join(text_lines))
