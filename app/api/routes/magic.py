import jwt
from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from supabase import Client

from app.core.config import get_settings
from app.db.supabase import get_supabase_client
from app.services.cita_service import CitaService
from app.templates.load_html import load_html

router = APIRouter(prefix="/magic", tags=["Magic Links"])

settings = get_settings()


def get_cita_service():
    return CitaService()


@router.get("/cancel-cita", response_class=HTMLResponse)
def cancel_cita_magic(
    token: str,
    service: CitaService = Depends(get_cita_service),
    supabase: Client = Depends(get_supabase_client)
):

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"]
        )

        if payload["action"] != "cancel_cita":
            return HTMLResponse(
                "<h1>Acción inválida</h1>",
                status_code=403
            )

    except Exception:
        return HTMLResponse(
            "<h1>Link inválido o expirado</h1>",
            status_code=401
        )

    service.delete_cita_magic(
        supabase=supabase,
        id_institucion=payload["institutionId"],
        id_cita=payload["citaId"],
        motivo="Cancelada desde WhatsApp",
        numero_documento=payload["numeroDocumento"],
        tipo_documento=payload["tipoDocumento"],
    )

    html = load_html("magic_cancel_success.html")

    return HTMLResponse(content=html)