from aiogram import Router

from .start import router as start_router
from .task import router as task_router
from .update_buttons import router as cats_router
from .cancel import router as actions_router
from .add import router as add_router
from .pager import router as pager_router
from .help import router as help_router


router = Router()
# Подключаем роутеры
router.include_routers(
    start_router,
    task_router,
    cats_router,
    actions_router,
    add_router,
    pager_router,
    help_router,
)

__all__ = ["router"]
