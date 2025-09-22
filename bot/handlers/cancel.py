from aiogram import Router, F
from aiogram import types
from aiogram.fsm.context import FSMContext
import httpx

from states.task import AddTask

from service.django_api import with_auto_refresh

from storage import store

from service import api

from utils.ui import fmt_task_line, kb_task_actions

router = Router()


@router.callback_query(F.data.regexp(r"^task:done:(\d+)$"))
async def cb_task_done(cb: types.CallbackQuery):
    task_id = int(cb.data.split(":")[2])
    try:
        updated = await with_auto_refresh(
            cb.message.chat.id,
            store,
            lambda access: api.update_task(access, task_id, {"status": "done"}),
            lambda refresh: api.refresh(refresh),
        )
        # обновим текст и кнопки (дедлайна может не быть уже важно; статус станет done)
        new_text = fmt_task_line(updated)
        await cb.message.edit_text(new_text, parse_mode="Markdown",
                                   reply_markup=kb_task_actions(updated["id"], bool(updated.get("due_at"))))
        await cb.answer("Готово ✓")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            await cb.answer("Не твоя задача или не найдена.", show_alert=True)
        else:
            await cb.answer(f"Ошибка {e.response.status_code}", show_alert=True)
    except Exception as e:
        await cb.answer(f"Ошибка: {e!s}", show_alert=True)


@router.callback_query(F.data.regexp(r"^task:cancel:(\d+)$"))
async def cb_task_cancel_due(cb: types.CallbackQuery):
    task_id = int(cb.data.split(":")[2])
    try:
        updated = await with_auto_refresh(
            cb.message.chat.id,
            store,
            lambda access: api.update_task(access, task_id, {"due_at": None}),
            lambda refresh: api.refresh(refresh),
        )
        new_text = fmt_task_line(updated)
        # после снятия дедлайна кнопку «Снять дедлайн» убираем
        await cb.message.edit_text(new_text, parse_mode="Markdown",
                                   reply_markup=kb_task_actions(updated["id"], has_due=False))
        await cb.answer("Дедлайн снят ✓")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            await cb.answer("Не твоя задача или не найдена.", show_alert=True)
        else:
            await cb.answer(f"Ошибка {e.response.status_code}", show_alert=True)
    except Exception as e:
        await cb.answer(f"Ошибка: {e!s}", show_alert=True)


@router.callback_query(AddTask.waiting_confirm, F.data == "create_cancel")
async def add_cancel(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("Создание отменено.")
    await cb.answer()


@router.callback_query(AddTask.waiting_confirm, F.data == "create_confirm")
async def add_confirm(cb: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    payload = {"title": data["title"]}
    if data.get("due"):
        payload["due_at"] = data["due"].isoformat()
    # Передадим выбранные категории, если они есть
    sel = data.get("selected") or []
    if sel:
        payload["category_ids"] = sel

    try:
        result = await with_auto_refresh(
            cb.message.chat.id,
            store,
            lambda access: api.create_task(access, payload),
            lambda refresh: api.refresh(refresh),
        )
        text = f"Создано ✅\n[id={result['id']}] {result['title']}\nДедлайн: {result.get('due_at') or '—'}"
        await cb.message.edit_text(text)
    except httpx.HTTPStatusError as e:
        await cb.message.edit_text(f"Ошибка {e.response.status_code}: {e.response.text}")
    except Exception as e:
        await cb.message.edit_text(f"Ошибка создания: {e!s}")
    finally:
        await state.clear()
        await cb.answer()
