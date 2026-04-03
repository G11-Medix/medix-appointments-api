from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_key)


@lru_cache
def get_supabase_admin_client() -> Client:
    settings = get_settings()
    service_role_key = settings.supabase_service_role_key or settings.supabase_key
    return create_client(settings.supabase_url, service_role_key)
