import contextlib

from aiogram.fsm.context import FSMContext
from aiogram import Router
from aiogram import types
from aiogram.filters import Command, CommandObject
import httpx
from aiogram.exceptions import TelegramBadRequest
import math
from service.django_api import with_auto_refresh
from utils.ui import fmt_task_line, kb_task_actions

from states.task import AddTask
from service import api
from storage import store

from utils.pager import (
    forget_page,
    remember_page,
    kb_pager,
    remember_ctrl,
    forget_ctrl,
    acquire_page_lock,
    release_page_lock,
    set_current,
)
from utils.auth import ensure_auth

router = Router()


@router.message(Command("tasks"))
async def tasks_cmd(message: types.Message):
    # простая защита от спама — пока рендерится список, игнорим повтор
    if not acquire_page_lock(message.chat.id):
        return
    # гарантируем авторизацию (после рестарта контейнера)
    await ensure_auth(message.chat.id, message.from_user)
    parts = message.text.strip().split()
    status = None
    if len(parts) == 2:
        mapping = {"todo": "todo", "done": "done", "in_progress": "in_progress", "in": "in_progress"}
        status = mapping.get(parts[1].lower())
        if status is None:
            await message.answer("Фильтр: /tasks, /tasks todo, /tasks done, /tasks in_progress")
            return

    page = 1
    # грузим 1-ю страницу
    data = await with_auto_refresh(
        message.chat.id, store,
        lambda access: api.list_tasks_paginated(access, status=status, page=page),
        lambda refresh: api.refresh(refresh)
    )
    # Поддержка обоих форматов: пагинация (dict) и без пагинации (list)
    if isinstance(data, dict):
        items = data.get("results", [])
        has_prev = data.get("previous") is not None
        has_next = data.get("next") is not None
        count = int(data.get("count", len(items) or 0))
        # предполагаем PAGE_SIZE=5 (как на бэке), чтобы показать число страниц
        total_pages = max(1, math.ceil(count / 5))
    else:
        items = list(data)
        has_prev = False
        has_next = False
        count = len(items)
        total_pages = 1

    # контроллер
    header = (
        f"Твои задачи (всего: {count}) — Стр. {page}/{total_pages}"
        if not status else
        f"Задачи ({status}) (всего: {count}) — Стр. {page}/{total_pages}"
    )
    # удалить предыдущий контроллер, если был
    old_ctrl = forget_ctrl(message.chat.id)
    if old_ctrl:
        with contextlib.suppress(Exception):
            await message.bot.delete_message(chat_id=message.chat.id, message_id=old_ctrl)
    # отправим контроллер; если по какой-то причине уже совпадает — просто продолжим
    try:
        ctrl = await message.answer(header, reply_markup=kb_pager(page, status, has_prev, has_next))
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            ctrl = message
        else:
            raise
    remember_ctrl(message.chat.id, ctrl.message_id)

    # удалить предыдущую страницу (если была) ДО вывода новых карточек
    for mid in forget_page(message.chat.id):
        with contextlib.suppress(Exception):
            await message.bot.delete_message(chat_id=message.chat.id, message_id=mid)

    # вывести карточки и запомнить их id
    shown_ids = []
    for t in items:
        text = fmt_task_line(t)
        has_due = bool(t.get("due_at"))
        msg = await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=kb_task_actions(t["id"], has_due, t.get("status"))
        )
        shown_ids.append(msg.message_id)
    remember_page(message.chat.id, shown_ids)
    set_current(message.chat.id, page, status)
    release_page_lock(message.chat.id)


@router.message(Command("done"))
async def mark_done(message: types.Message, command: CommandObject):
    """
    /done <id> — поставить статус done.
    """
    if not command.args:
        await message.answer("Используй: /done <id>")
        return
    try:
        task_id = int(command.args.strip())
    except ValueError:
        await message.answer("id должен быть числом.")
        return

    try:
        await ensure_auth(message.chat.id, message.from_user)
        result = await with_auto_refresh(
            message.chat.id,
            store,
            lambda access: api.update_task(access, task_id, {"status": "done"}),
            lambda refresh: api.refresh(refresh),
        )
        await message.answer(f"Готово ✅\n[{result['id']}] {result['title']} → done")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            await message.answer("Задача не найдена или не твоя.")
        elif e.response.status_code == 400:
            await message.answer(f"Неверные данные: {e.response.text}")
        else:
            await message.answer(f"Ошибка: {e.response.status_code}")
    except Exception as e:
        await message.answer(f"Ошибка запроса: {e!s}")


@router.message(Command("cancel"))
async def cancel_due(message: types.Message, command: CommandObject):
    """
    /cancel <id> — убрать дедлайн у задачи.
    """
    if not command.args:
        await message.answer("Используй: /cancel <id>")
        return
    try:
        task_id = int(command.args.strip())
    except ValueError:
        await message.answer("id должен быть числом.")
        return

    try:
        await ensure_auth(message.chat.id, message.from_user)
        result = await with_auto_refresh(
            message.chat.id,
            store,
            lambda access: api.update_task(access, task_id, {"due_at": None}),
            lambda refresh: api.refresh(refresh),
        )
        await message.answer(f"Дедлайн снят ✅\n[{result['id']}] {result['title']}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            await message.answer("Задача не найдена или не твоя.")
        else:
            await message.answer(f"Ошибка: {e.response.status_code}")
    except Exception as e:
        await message.answer(f"Ошибка запроса: {e!s}")
