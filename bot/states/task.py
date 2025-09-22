from aiogram.fsm.state import StatesGroup, State

# Состояния диалога добавления задачи
class AddTask(StatesGroup):
    """
    Диалог добавления задачи:
    1. Ввод заголовка
    2. Ввод дедлайна
    3. Выбор категорий
    4. Подтверждение создания
    """
    waiting_title = State() # ввод заголовка
    waiting_due = State() # ввод дедлайна
    waiting_categories = State() # выбор категорий
    waiting_confirm = State() # подтверждение создания
