from fastapi import APIRouter

from .start import router as start_router

router = APIRouter()

# Use empty prefix so routes are mounted at root. FastAPI forbids trailing '/'.
router.include_router(start_router, prefix="/internal", tags=["internal"])
