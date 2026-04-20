from supabase import Client


class LogAuditoriaRepository:
    def insert(self, supabase: Client, payload: dict) -> None:
        supabase.table("Log_Auditoria").insert(payload).execute()
