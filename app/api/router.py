from fastapi import APIRouter, Depends

from app.api.dependencies.auth import require_active_user
from app.api.routes.assistant import router as assistant_router
from app.api.routes.cita import patient_router as cita_patient_router
from app.api.routes.cita import router as cita_router
from app.api.routes.institucion import router as institucion_router
from app.api.routes.paciente import protected_router as paciente_router
from app.api.routes.consentimiento import router as consentimiento_router
from app.api.routes.recomendacion import router as recomendacion_router
from app.api.routes.dispositivos_usuario import router as dispositivos_usuario_router


api_router = APIRouter(dependencies=[Depends(require_active_user)])
api_router.include_router(assistant_router)
api_router.include_router(institucion_router)
api_router.include_router(paciente_router)
api_router.include_router(cita_router)
api_router.include_router(cita_patient_router)
api_router.include_router(consentimiento_router)
api_router.include_router(recomendacion_router)
api_router.include_router(dispositivos_usuario_router)
