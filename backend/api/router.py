from fastapi import APIRouter

from api.v1.router import v1_router

router = APIRouter(prefix="/api")
router.include_router(v1_router)
