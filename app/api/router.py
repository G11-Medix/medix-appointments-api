from fastapi import APIRouter

from app.api.routes.institucion import router as institucion_router

api_router = APIRouter()
api_router.include_router(institucion_router)
