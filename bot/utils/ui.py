from datetime import datetime, timezone
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# def fmt_task_line(t: dict) -> str:
#     """
#     Сформировать строку (многострочный Markdown) для одной задачи.
#     Ожидает структуру из Django API.
#     """
#     cats = ", ".join(c.get("name", "") for c in t.get("categories", [])) or "—"
#     lines = [
#         f"• [{t['id']}] {t['title']} [{t['status']}]",
#         f"  Категории: {cats}",
#         f"  Создано: {t.get('created_at')}",
#         f"  Дедлайн: {t.get('due_at') or '—'}",
#     ]
#     return "\n".join(lines)


# def kb_task_actions(task_id: int, has_due: bool) -> InlineKeyboardMarkup:
#     """
#     Кнопки действий по задаче. Используем switch_inline_query_current_chat,
#     чтобы подставить готовую команду (/done, /cancel) в поле ввода.
#     Это не требует отдельной обработки callback-ов.
#     """
#     row = [
#         InlineKeyboardButton(text="✅ Done", switch_inline_query_current_chat=f"/done {task_id}"),
#     ]
#     if has_due:
#         row.append(InlineKeyboardButton(text="⏰ Снять дедлайн", switch_inline_query_current_chat=f"/cancel {task_id}"))
#     return InlineKeyboardMarkup(inline_keyboard=[row])


def escape_md(text: str) -> str:
    """простое экранирование для MarkdownV2/Markdown (мы используем parse_mode='Markdown')."""
    return (text or "").replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")


def humanize_timedelta(td) -> str:
    secs = int(td.total_seconds())
    if secs <= 0: return "0м"
    m, s = divmod(secs, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    parts = []
    if d: parts.append(f"{d}д")
    if h: parts.append(f"{h}ч")
    if m: parts.append(f"{m}м")
    return " ".join(parts) or "менее минуты"


def fmt_task_line(t: dict) -> str:
    title = escape_md(t["title"])
    cats = ", ".join(escape_md(c["name"]) for c in t.get("categories", [])) or "—"
    created = t["created_at"]
    due = t.get("due_at") or "—"
    return (
        f"• [{t['id']}] *{title}* [{t['status']}]\n"
        f"  Категории: {cats}\n"
        f"  Создано: {created}\n"
        f"  Дедлайн: {due}"
    )


def kb_task_actions(task_id: int, has_due: bool, status: str | None = None) -> InlineKeyboardMarkup:
    """Клавиатура действий по задаче.
    Если статус уже done — кнопку "Готово" не показываем.
    :param task_id: id задачи
    :param has_due: есть ли дедлайн
    :param status: текущий статус (может быть None, тогда считаем не done)
    """
    buttons = []
    if status != "done":
        buttons.append(InlineKeyboardButton(text="✅ Готово", callback_data=f"task:done:{task_id}"))
    if has_due:
        buttons.append(InlineKeyboardButton(text="🗓 Снять дедлайн", callback_data=f"task:cancel:{task_id}"))
    if not buttons:
        # хотя бы пустой ряд, чтобы не падать — или можно вернуть None и не прикреплять клавиатуру выше
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="—", callback_data="noop")]])
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def kb_confirm_create() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Создать", callback_data="create_confirm"),
        InlineKeyboardButton(text="✖️ Отмена", callback_data="create_cancel"),
    ]])


def fmt_task_preview(title: str, due: datetime | None) -> str:
    lines = [f"📝 *Новая задача*", f"• Заголовок: *{escape_md(title)}*"]
    if due:
        now = datetime.now(timezone.utc) if due.tzinfo else datetime.utcnow()
        left = humanize_timedelta(due - now)
        lines.append(f"• Дедлайн: *{due.isoformat()}*  _(осталось {left})_")
    else:
        lines.append("• Дедлайн: *—*")
    return "\n".join(lines)


def kb_categories_page(cats: list[dict], page: int, has_prev: bool, has_next: bool, selected: set[int]):
    rows = []
    # чекбоксы
    for c in cats:
        cid = c["id"]
        checked = "☑" if cid in selected else "⬜"
        rows.append([InlineKeyboardButton(text=f"{checked} {c['name']}", callback_data=f"cat:toggle:{cid}")])
    # пагинация
    row = []
    if has_prev: row.append(InlineKeyboardButton(text="◀️", callback_data=f"cat:page:{page - 1}"))
    row.append(InlineKeyboardButton(text=f"Стр. {page}", callback_data="noop"))
    if has_next: row.append(InlineKeyboardButton(text="▶️", callback_data=f"cat:page:{page + 1}"))
    rows.append(row)
    # действия
    rows.append([
        InlineKeyboardButton(text="➕ Создать", callback_data="cat:new"),
        InlineKeyboardButton(text="Дальше →", callback_data="cat:next"),
        InlineKeyboardButton(text="Пропустить", callback_data="cat:skip"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
