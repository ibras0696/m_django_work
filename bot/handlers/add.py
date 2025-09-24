from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from datetime import timezone

from utils import parse_due
from utils.ui import fmt_task_preview, kb_confirm_create, kb_categories_page
from states.task import AddTask
from service.django_api import with_auto_refresh
from service import api
from storage import store
from config import INTERNAL_TOKEN

router = Router()


async def _ensure_auth(chat_id: int, user: types.User):
    """Если токенов нет (после перезапуска контейнера), авторизуемся через bot_auth."""
    auth = await store.get_auth(chat_id)
    if auth:
        return
    payload = {
        "telegram_user_id": user.id,
        "chat_id": chat_id,
        "username": user.username or "",
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
    }
    res = api.bot_auth(payload, INTERNAL_TOKEN)
    access, refresh = res["access"], res["refresh"]
    user_id = int(res["user"]["id"])
    await store.upsert_tokens(chat_id, user_id, access, refresh)

@router.message(Command("add"))
async def add_start(message: types.Message, state: FSMContext):
    # гарантируем авторизацию
    await _ensure_auth(message.chat.id, message.from_user)
    await state.set_state(AddTask.waiting_title)
    await message.answer("Введи заголовок задачи:")


@router.message(AddTask.waiting_title)
async def add_got_title(message: types.Message, state: FSMContext):
    # если контейнер перезапущен между шагами — восстановим авторизацию
    await _ensure_auth(message.chat.id, message.from_user)
    title = message.text.strip()
    if not title:
        await message.answer("Заголовок пустой. Введи ещё раз:")
        return
    # Держим selected как список (FSM storage может не любить set)
    await state.update_data(title=title, cat_page=1, selected=[])
    await state.set_state(AddTask.waiting_categories)

    # показать страницу 1
    data = await with_auto_refresh(
        message.chat.id, store,
        lambda access: api.list_categories_paginated(access, page=1),
        lambda refresh: api.refresh(refresh)
    )
    if isinstance(data, dict):
        cats = data.get("results", [])
        has_prev = data.get("previous") is not None
        has_next = data.get("next") is not None
    else:
        cats = list(data)
        has_prev = False
        has_next = False
    kb = kb_categories_page(cats, page=1, has_prev=has_prev, has_next=has_next, selected=set())
    await message.answer("Выбери категории (можно несколько), потом нажми «Дальше →».", reply_markup=kb)


@router.message(AddTask.waiting_due)
async def add_got_due(message: types.Message, state: FSMContext):
    raw = (message.text or "").strip()
    due = None
    if raw.lower() != "skip":
        due = parse_due(raw)
        if not due:
            await message.answer("Не понял дату. Попробуй снова (ISO/`in 10m`/`today 20:00`).")
            return

    # нормализуем к timezone-aware
    if due and (due.tzinfo is None):
        due = due.replace(tzinfo=timezone.utc)

    await state.update_data(due=due)
    data = await state.get_data()
    preview = fmt_task_preview(data["title"], due)
    await state.set_state(AddTask.waiting_confirm)
    await message.answer(preview, reply_markup=kb_confirm_create(), parse_mode="Markdown")
