from aiogram import Router, F
from aiogram import types
from aiogram.fsm.context import FSMContext
import httpx

from states.task import AddTask
from service.django_api import with_auto_refresh
from storage import store
from service import api
from utils.ui import fmt_task_line, kb_task_actions, kb_categories_page

router = Router()


@router.callback_query(AddTask.waiting_categories, F.data.regexp(r"^cat:page:(\d+)$"))
async def cat_page(cb: types.CallbackQuery, state: FSMContext):
    page = int(cb.data.split(":")[2])
    d = await state.get_data()
    selected = set(d.get("selected", []))
    data = await with_auto_refresh(
        cb.message.chat.id, store,
        lambda access: api.list_categories_paginated(access, page=page),
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
    await state.update_data(cat_page=page)
    await cb.message.edit_reply_markup(reply_markup=kb_categories_page(cats, page, has_prev, has_next, selected))
    await cb.answer()


@router.callback_query(AddTask.waiting_categories, F.data.regexp(r"^cat:toggle:(\d+)$"))
async def cat_toggle(cb: types.CallbackQuery, state: FSMContext):
    cid = int(cb.data.split(":")[2])
    d = await state.get_data()
    page = int(d.get("cat_page", 1))
    selected = set(d.get("selected", []))
    if cid in selected:
        selected.remove(cid)
    else:
        selected.add(cid)
    await state.update_data(selected=list(selected))

    # перерисовать текущую страницу (чтобы чекбоксы обновились)
    data = await with_auto_refresh(
        cb.message.chat.id, store,
        lambda access: api.list_categories_paginated(access, page=page),
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
    await cb.message.edit_reply_markup(reply_markup=kb_categories_page(cats, page, has_prev, has_next, selected))
    await cb.answer()


@router.callback_query(AddTask.waiting_categories, F.data == "cat:new")
async def cat_new(cb: types.CallbackQuery, state: FSMContext):
    await state.update_data(awaiting_new_cat=1)
    await cb.message.answer("Введи название новой категории:")
    await cb.answer()


@router.message(AddTask.waiting_categories)
async def cat_new_name(message: types.Message, state: FSMContext):
    d = await state.get_data()
    if not d.get("awaiting_new_cat"):
        return  # игнор текста, если не ждём имя категории
    name = message.text.strip()
    if not name:
        await message.answer("Название пустое. Попробуй снова:")
        return
    try:
        cat = await with_auto_refresh(
            message.chat.id, store,
            lambda access: api.create_category(access, name),
            lambda refresh: api.refresh(refresh)
        )
        # добавим созданную категорию к выбранным
        selected = set(d.get("selected", []))
        selected.add(cat["id"])
        await state.update_data(selected=list(selected), awaiting_new_cat=0)
        await message.answer(f"Категория создана: {cat['name']} ✓")
    except Exception as e:
        await message.answer(f"Ошибка создания категории: {e!s}")


@router.callback_query(AddTask.waiting_categories, F.data == "cat:skip")
async def cat_skip(cb: types.CallbackQuery, state: FSMContext):
    await state.update_data(selected=[])
    await state.set_state(AddTask.waiting_due)
    await cb.message.edit_text("Категории пропущены. Теперь введи дедлайн (или `skip`).")
    await cb.answer()


@router.callback_query(AddTask.waiting_categories, F.data == "cat:next")
async def cat_next(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddTask.waiting_due)
    await cb.message.edit_text("Ок. Теперь дедлайн (ISO/`in 10m`/`today 20:00`). Если без дедлайна — напиши `skip`.")
    await cb.answer()
