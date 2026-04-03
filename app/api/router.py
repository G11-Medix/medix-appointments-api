from fastapi import APIRouter, Depends

from app.api.dependencies.auth import require_active_user
from app.api.routes.auth import admin_router as auth_admin_router
from app.api.routes.cita import router as cita_router
from app.api.routes.institucion import router as institucion_router
from app.api.routes.paciente import router as paciente_router

api_router = APIRouter(dependencies=[Depends(require_active_user)])
api_router.include_router(auth_admin_router)
api_router.include_router(institucion_router)
api_router.include_router(paciente_router)
api_router.include_router(cita_router)
