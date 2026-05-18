# Medix Appointments API

API backend en FastAPI para autenticación, catálogos médicos, pacientes, citas, consentimiento, recomendaciones, dispositivos de usuario, magic links y comunicación con IPS externas vía endpoints FHIR.

## Ejecutar local

Crear y activar entorno

```bash
python3 -m venv venv
source venv/bin/activate
```

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

## Variables de entorno

Crea un archivo `.env` a partir de `.env.example`.

Variables principales:

- `ENVIRONMENT`: entorno de ejecución.
- `SUPABASE_URL`: URL del proyecto Supabase.
- `SUPABASE_KEY`: llave anon/service usada por la API.
- `SUPABASE_SERVICE_ROLE_KEY`: llave service-role para operaciones administrativas; si no se define, se usa `SUPABASE_KEY`.
- `JWT_SECRET`: secreto para validar magic links.
- `IPS_ROUTES_JSON`: mapa JSON de `id_institucion` a URL de IPS.
- `IPS_TIMEOUT_SECONDS`: timeout HTTP para IPS.
- `NATS_ENABLED`: habilita o deshabilita el servidor NATS.
- `NATS_URL`: URL del servidor NATS.
- `NATS_SUBJECT_PREFIX`: prefijo de subjects NATS.
- `NATS_QUEUE_GROUP`: grupo de cola NATS.

## Docs

```text
http://localhost:8001/docs
http://localhost:8001/redoc
```

## Autenticación

- Todos los endpoints bajo `/api/*` requieren `Authorization: Bearer <token>`.
- El token se valida contra Supabase (`auth.get_user`).
- Además, el usuario debe existir en tabla `Usuario` con estado `ACTIVO`.
- `GET /auth/eligibility/{telefono}` permanece público y responde si un paciente está habilitado para OTP por teléfono.
- `POST /api/pacientes/` permite registrar un paciente con token Supabase válido y crea/activa el usuario local.
- `GET /magic/cancel-cita` es público y se protege mediante token firmado.
- Respuestas de acceso:
  - `401` para token ausente, malformado, inválido o expirado.
  - `403` para token válido sin registro local en `Usuario` o con estado distinto de `ACTIVO`.
- Rutas fuera de `/api/*` (`/`, `/docs`, `/redoc`, `/openapi.json`, `/auth/*`, `/magic/*`) permanecen públicas o protegidas por su propio mecanismo.

## Auditoría automática

- Se auditan todas las operaciones bajo `/api/*`.
- Cada request auditada intenta insertar un registro en `Log_Auditoria`.
- `id_usuario` se reutiliza desde el contexto autenticado del request.
- `resultado`:
  - `EXITO` para status `< 400`
  - `ERROR` para status `>= 400` o excepciones no controladas
- Política fail-open: si falla insertar el log, la API responde normalmente.

## Pruebas

```bash
pytest
```

## Build and Run (Docker Compose)

```bash
docker compose up --build
```

El `docker-compose.yml` ya deja configurado `IPS_ROUTES_JSON` para enrutar:
- `2` -> `ips_santa_fe:4011`
- `3` -> `ips_country:4012`
- `4` -> `ips_clinica_colombia:4013`
- `5` -> `ips_san_ignacio:4014`
- `6` -> `ips_mederi:4015`

## Build and Run (Docker)

```bash
docker build -t medix-api -f Dockerfile .
docker run --env-file .env -p 8001:8001 medix-api
```
