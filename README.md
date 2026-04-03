
### Ejecutar local

Crear y activar entorno

```bash
python3 -m venv venv
source venv/bin/activate
```

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Docs

```curl
http://localhost:8000/docs
http://localhost:8000/redoc
```

### Autenticación

- Todos los endpoints bajo `/api/*` requieren `Authorization: Bearer <token>`.
- El token se valida contra Supabase (`auth.get_user`).
- Además, el usuario debe existir en tabla `Usuario` con estado `ACTIVO`.
- `GET /auth/eligibility/{telefono}` permanece público y responde si un paciente está habilitado para OTP por teléfono.
- `POST /api/admin/pacientes/{id_paciente}/grant-access` requiere un usuario autenticado con rol administrativo (`ADMIN`, `ADMINISTRADOR` o `SUPERADMIN`).
- La provisión administrativa usa `SUPABASE_SERVICE_ROLE_KEY` solo en backend para crear o reconciliar usuarios en Supabase Auth.
- Respuestas de acceso:
  - `401` para token ausente, malformado, inválido o expirado.
  - `403` para token válido sin registro local en `Usuario` o con estado distinto de `ACTIVO`.
- Rutas fuera de `/api/*` (`/`, `/docs`, `/redoc`, `/openapi.json`) permanecen públicas.

### Auditoría automática

- Se auditan todas las operaciones bajo `/api/*`.
- Cada request auditada intenta insertar un registro en `Log_Auditoria`.
- `id_usuario` se reutiliza desde el contexto autenticado del request.
- `resultado`:
  - `EXITO` para status `< 400`
  - `ERROR` para status `>= 400` o excepciones no controladas
- Política fail-open: si falla insertar el log, la API responde normalmente.

### Pruebas

```bash
pytest
```

### Build and Run (Docker)

```bash
docker build -t medix-api -f dockerfile .
docker run --env-file .env -p 8000:8000 medix-api
```
