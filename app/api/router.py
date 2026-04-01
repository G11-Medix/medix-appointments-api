from fastapi import APIRouter

from app.api.routes.cita import router as cita_router
from app.api.routes.institucion import router as institucion_router
from app.api.routes.paciente import router as paciente_router

api_router = APIRouter()
api_router.include_router(institucion_router)
api_router.include_router(paciente_router)
api_router.include_router(cita_router)
