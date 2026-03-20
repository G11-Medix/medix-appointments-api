### Variables de entorno

1. Copia `.env.example` a `.env`.
2. Completa las variables del SDK de Supabase:
- `SUPABASE_URL=https://[TU_PROJECT_REF].supabase.co`
- `SUPABASE_KEY=[TU_SUPABASE_SERVICE_ROLE_KEY]`

### Ejecutar local

Activar entorno

```bash
source venv/bin/activate
```

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Endpoints disponibles

- `GET /`
- `GET /api/instituciones/?limit=20`

### Build and Run (Docker)

```bash
docker build -t medix-api -f dockerfile .
docker run --env-file .env -p 8000:8000 medix-api
```
