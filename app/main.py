from fastapi import FastAPI

from app.api.routes.auth import public_router as auth_public_router
from app.api.middlewares.audit_middleware import build_audit_middleware
from app.api.router import api_router
from app.db.supabase import get_supabase_client

app = FastAPI(title="Medix Appointments API")
supabase = get_supabase_client()
app.middleware("http")(build_audit_middleware(supabase))
app.include_router(auth_public_router)
app.include_router(api_router, prefix="/api")


@app.get("/")
def hello_world() -> dict[str, str]:
    return {"message": "Hello World"}
