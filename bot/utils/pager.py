from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# простой in-memory кэш: какие сообщения с задачами сейчас выведены для чата
PAGE_CACHE: dict[int, list[int]] = {}
# храним id сообщения-контроллера ("Стр. N"), чтобы удалять старый при новом /tasks
CTRL_CACHE: dict[int, int] = {}
_BUSY: set[int] = set()
CURRENT_STATE: dict[int, tuple[int, str|None]] = {}

def remember_page(chat_id: int, msg_ids: list[int]):
    PAGE_CACHE[chat_id] = msg_ids

def forget_page(chat_id: int) -> list[int]:
    return PAGE_CACHE.pop(chat_id, [])

def remember_ctrl(chat_id: int, msg_id: int):
    CTRL_CACHE[chat_id] = msg_id

def forget_ctrl(chat_id: int) -> int | None:
    return CTRL_CACHE.pop(chat_id, None)

def kb_pager(page: int, status: str|None, has_prev: bool, has_next: bool):
    st = status or "-"
    row = []
    # всегда рисуем стрелки; если листать нельзя — делаем noop
    left_cb = f"tasks:page:{page-1}:{st}" if has_prev else "noop"
    right_cb = f"tasks:page:{page+1}:{st}" if has_next else "noop"
    row.append(InlineKeyboardButton(text="◀️", callback_data=left_cb))
    # центр — noop, не перерисовываем текущую страницу
    row.append(InlineKeyboardButton(text=f"Стр. {page}", callback_data="noop"))
    row.append(InlineKeyboardButton(text="▶️", callback_data=right_cb))
    return InlineKeyboardMarkup(inline_keyboard=[row])

def kb_pager_compact(page: int, status: str|None, has_prev: bool, has_next: bool):
    st = status or "-"
    row = []
    if has_prev:
        row.append(InlineKeyboardButton(text="◀️", callback_data=f"tasksC:page:{page-1}:{st}"))
    row.append(InlineKeyboardButton(text=f"Стр. {page}", callback_data="noop"))
    if has_next:
        row.append(InlineKeyboardButton(text="▶️", callback_data=f"tasksC:page:{page+1}:{st}"))
    return InlineKeyboardMarkup(inline_keyboard=[row])

__all__ = [
    "remember_page",
    "forget_page",
    "kb_pager",
    "kb_pager_compact",
    "remember_ctrl",
    "forget_ctrl",
]

# простая блокировка на время перерисовки страницы, чтобы не плодить дубли при быстрых нажатиях
def acquire_page_lock(chat_id: int) -> bool:
    if chat_id in _BUSY:
        return False
    _BUSY.add(chat_id)
    return True

def release_page_lock(chat_id: int):
    _BUSY.discard(chat_id)

def set_current(chat_id: int, page: int, status: str|None):
    CURRENT_STATE[chat_id] = (page, status)

def get_current(chat_id: int) -> tuple[int, str|None] | None:
    return CURRENT_STATE.get(chat_id)

__all__ += [
    "acquire_page_lock",
    "release_page_lock",
    "set_current",
    "get_current",
]