from fastapi import FastAPI, HTTPException

from app.api.router import api_router
from app.db.supabase import get_supabase_client

app = FastAPI(title="Medix Appointments API")
app.include_router(api_router, prefix="/api")
supabase = get_supabase_client()


@app.get("/")
def hello_world() -> dict[str, str]:
    return {"message": "Hello World"}
