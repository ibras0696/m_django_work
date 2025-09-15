from aiogram import Router

from .start import router as start_router

router = Router()
# include_router (singular) is the correct method on aiogram.Router
router.include_router(start_router)


__all__ = ["router"]