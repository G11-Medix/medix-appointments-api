
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

### Auditoría automática

- Se auditan todas las operaciones bajo `/api/*`.
- Cada request auditada intenta insertar un registro en `Log_Auditoria`.
- `id_usuario` se resuelve desde JWT Bearer validado con Supabase (`auth.get_user`).
- `resultado`:
  - `EXITO` para status `< 400`
  - `ERROR` para status `>= 400` o excepciones no controladas
- Política fail-open: si falla insertar el log, la API responde normalmente.

### Build and Run (Docker)

```bash
docker build -t medix-api -f dockerfile .
docker run --env-file .env -p 8000:8000 medix-api
```
