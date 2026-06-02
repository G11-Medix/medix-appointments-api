from html import escape

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


def _decode_cancel_cita_token(token: str) -> dict | HTMLResponse:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
        )

        if payload["action"] != "cancel_cita":
            return HTMLResponse(
                "<h1>Acción inválida</h1>",
                status_code=403,
            )

        return payload

    except Exception:
        return HTMLResponse(
            "<h1>Link inválido o expirado</h1>",
            status_code=401,
        )


@router.get("/cancel-cita", response_class=HTMLResponse)
def confirm_cancel_cita_magic(token: str):
    payload = _decode_cancel_cita_token(token)
    if isinstance(payload, HTMLResponse):
        return payload

    safe_token = escape(token, quote=True)
    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>Confirmar cancelación | Medix</title>
            <style>
                body {{
                    font-family: Arial;
                    background: #f4f7fb;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                }}
                .card {{
                    background: white;
                    padding: 32px;
                    border-radius: 16px;
                    box-shadow: 0 10px 25px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 420px;
                }}
                h1 {{
                    color: #1f2937;
                    font-size: 24px;
                }}
                p {{
                    color: #4b5563;
                    margin-top: 10px;
                }}
                button {{
                    margin-top: 20px;
                    border: 0;
                    padding: 12px 18px;
                    background: #dc2626;
                    color: white;
                    border-radius: 10px;
                    cursor: pointer;
                    font-size: 16px;
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>Confirmar cancelación</h1>
                <p>Presiona el botón para cancelar la cita.</p>
                <form method="post" action="?token={safe_token}">
                    <button type="submit">Cancelar cita</button>
                </form>
            </div>
        </body>
        </html>
        """
    )


@router.post("/cancel-cita", response_class=HTMLResponse)
def cancel_cita_magic(
    token: str,
    service: CitaService = Depends(get_cita_service),
    supabase: Client = Depends(get_supabase_client),
):
    payload = _decode_cancel_cita_token(token)
    if isinstance(payload, HTMLResponse):
        return payload

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
