from aiogram import Router

from .start import router as start_router
from .task import router as task_router

router = Router()
# Подключаем роутеры
router.include_routers(start_router, task_router)

__all__ = ["router"]
