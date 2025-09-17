from aiogram.fsm.state import StatesGroup, State


class AddTask(StatesGroup):
    waiting_title = State()
    waiting_due = State()
