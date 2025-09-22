from aiogram import Router, types
from aiogram.filters import Command

router = Router()

HELP_TEXT = (
    "Привет! Я помогу управлять задачами. Доступные команды:\n\n"
    "• /start — авторизация бота и приветствие\n"
    "• /help — эта справка\n"
    "• /tasks [todo|in_progress|done] — список задач с пагинацией (по 5 на страницу)\n"
    "    - Листай стрелками ◀️ ▶️\n"
    "    - Кнопка ‘Стр. N’ — обновляет текущую страницу\n"
    "• /tasks_compact [фильтр] — компактный режим: все задачи страницы одним сообщением\n"
    "• /done <id> — отметить задачу выполненной\n"
    "• /cancel <id> — снять дедлайн\n"
    "• /add — добавить новую задачу (заголовок → категории → дедлайн → подтверждение)\n"
)


@router.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.answer(HELP_TEXT)
