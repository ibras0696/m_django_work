import contextlib
import math

from aiogram import Router, types, F
from aiogram.exceptions import TelegramBadRequest

from utils.pager import (
    forget_page,
    remember_page,
    kb_pager,
    acquire_page_lock,
    release_page_lock,
    get_current,
    set_current,
)
from utils.ui import fmt_task_line, kb_task_actions
from utils.auth import ensure_auth
from service.django_api import with_auto_refresh
from storage import store
from service import api

router = Router()


@router.callback_query(F.data.regexp(r"^tasks:page:(\d+):(.+)$"))
async def tasks_page(cb: types.CallbackQuery):
    if not acquire_page_lock(cb.message.chat.id):
        await cb.answer()
        return
    # гарантируем авторизацию на всякий случай
    await ensure_auth(cb.message.chat.id, cb.from_user)
    page = int(cb.data.split(":")[2])
    st = cb.data.split(":")[3]
    status = None if st == "-" else st

    # если просим ту же страницу и статус — ничего не делаем
    cur = get_current(cb.message.chat.id)
    if cur and cur == (page, status):
        release_page_lock(cb.message.chat.id)
        await cb.answer()
        return

    data = await with_auto_refresh(
        cb.message.chat.id, store,
        lambda access: api.list_tasks_paginated(access, status=status, page=page),
        lambda refresh: api.refresh(refresh)
    )
    if isinstance(data, dict):
        items = data.get("results", [])
        has_prev = data.get("previous") is not None
        has_next = data.get("next") is not None
        count = int(data.get("count") or len(items) or 0)
        total_pages = max(1, math.ceil(count / 5))
    else:
        items = list(data)
        has_prev = False
        has_next = False
        count = len(items)
        total_pages = 1

    # сначала удалим карточки предыдущей страницы, потом обновим контроллер
    prev_ids = forget_page(cb.message.chat.id)
    for mid in prev_ids:
        with contextlib.suppress(Exception):
            await cb.message.bot.delete_message(chat_id=cb.message.chat.id, message_id=mid)
    # обновим заголовок-контроллер текстом и клавиатурой
    header = (
        f"Твои задачи (всего: {count}) — Стр. {page}/{total_pages}"
        if not status else
        f"Задачи ({status}) (всего: {count}) — Стр. {page}/{total_pages}"
    )
    try:
        await cb.message.edit_text(header, reply_markup=kb_pager(page, status, has_prev, has_next))
    except TelegramBadRequest as e:
        # Игнорируем «message is not modified»
        if "message is not modified" not in str(e):
            raise

    # покажем карточки новой страницы и запомним ids
    shown_ids = []
    for t in items:
        text = fmt_task_line(t)
        has_due = bool(t.get("due_at"))
        msg = await cb.message.answer(text, parse_mode="Markdown", reply_markup=kb_task_actions(t["id"], has_due))
        shown_ids.append(msg.message_id)
    remember_page(cb.message.chat.id, shown_ids)

    set_current(cb.message.chat.id, page, status)
    release_page_lock(cb.message.chat.id)
    await cb.answer()


@router.callback_query(F.data == "noop")
async def pager_noop(cb: types.CallbackQuery):
    # просто скрыть спиннер, когда ткнули в «Стр. N» — без текста
    await cb.answer()


## удалён tasks:refresh — центральная кнопка теперь noop


# Компактный режим: одна карточка-список, перелистывание через tasksC:page
from utils.pager import kb_pager_compact


def _format_tasks_compact(items: list[dict]) -> str:
    if not items:
        return "Задач нет"
    lines = ["Задачи:"]
    for t in items:
        title = t.get("title", "—")
        tid = t.get("id")
        status = t.get("status")
        lines.append(f"• [{tid}] {title} [{status}]")
    return "\n".join(lines)


@router.message(F.text.regexp(r"^/tasks_compact(\s+\w+)?$"))
async def tasks_compact_cmd(message: types.Message):
    # гарантируем авторизацию
    await ensure_auth(message.chat.id, message.from_user)
    parts = message.text.strip().split()
    status = None
    if len(parts) == 2:
        mapping = {"todo": "todo", "done": "done", "in_progress": "in_progress", "in": "in_progress"}
        status = mapping.get(parts[1].lower())
        if status is None:
            await message.answer("Фильтр: /tasks_compact, /tasks_compact todo, /tasks_compact done, /tasks_compact in_progress")
            return
    page = 1
    data = await with_auto_refresh(
        message.chat.id, store,
        lambda access: api.list_tasks_paginated(access, status=status, page=page),
        lambda refresh: api.refresh(refresh)
    )
    if isinstance(data, dict):
        items = data.get("results", [])
        has_prev = data.get("previous") is not None
        has_next = data.get("next") is not None
    else:
        items = list(data)
        has_prev = False
        has_next = False
    text = _format_tasks_compact(items)
    await message.answer(text, reply_markup=kb_pager_compact(page, status, has_prev, has_next))


@router.callback_query(F.data.regexp(r"^tasksC:page:(\d+):(.+)$"))
async def tasks_compact_page(cb: types.CallbackQuery):
    await ensure_auth(cb.message.chat.id, cb.from_user)
    page = int(cb.data.split(":")[2])
    st = cb.data.split(":")[3]
    status = None if st == "-" else st
    data = await with_auto_refresh(
        cb.message.chat.id, store,
        lambda access: api.list_tasks_paginated(access, status=status, page=page),
        lambda refresh: api.refresh(refresh)
    )
    if isinstance(data, dict):
        items = data.get("results", [])
        has_prev = data.get("previous") is not None
        has_next = data.get("next") is not None
    else:
        items = list(data)
        has_prev = False
        has_next = False
    text = _format_tasks_compact(items)
    try:
        await cb.message.edit_text(text, reply_markup=kb_pager_compact(page, status, has_prev, has_next))
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
    await cb.answer()
