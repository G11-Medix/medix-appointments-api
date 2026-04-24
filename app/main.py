from fastapi import FastAPI

from app.api.routes.auth import public_router as auth_public_router
from app.api.routes.eps import router as eps_router
from app.api.routes.paciente import registration_router as paciente_registration_router
from app.api.middlewares.audit_middleware import build_audit_middleware
from app.api.router import api_router
from app.db.supabase import get_supabase_client
from app.messaging.nats_handlers import NatsApiHandlers
from app.messaging.nats_server import NatsRequestReplyServer

app = FastAPI(title="Medix Appointments API")
supabase = get_supabase_client()
app.middleware("http")(build_audit_middleware(supabase))
app.include_router(auth_public_router)
app.include_router(eps_router, prefix="/api")
app.include_router(paciente_registration_router, prefix="/api")
app.include_router(api_router, prefix="/api")


@app.on_event("startup")
async def startup_nats_server() -> None:
    server = NatsRequestReplyServer(handlers=NatsApiHandlers(supabase=supabase))
    app.state.nats_server = server
    await server.start()


@app.on_event("shutdown")
async def shutdown_nats_server() -> None:
    server = getattr(app.state, "nats_server", None)
    if server is not None:
        await server.close()


@app.get("/")
def hello_world() -> dict[str, str]:
    return {"message": "Hello World"}
