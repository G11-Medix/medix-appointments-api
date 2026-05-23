# Medix Appointments API

API backend para la gestión de citas médicas del ecosistema Medix. Este repositorio resuelve la exposición de servicios de autenticación, catálogos médicos, pacientes, citas, consentimiento, recomendaciones, dispositivos de usuario e integración con IPS externas dentro del proyecto de grado.

## Descripción general

Este repositorio implementa una API REST construida con FastAPI para centralizar operaciones relacionadas con la agenda médica de Medix.

Pertenece al sistema backend del proyecto y funciona como servicio de citas, pacientes y catálogos médicos. También incorpora integración con Supabase para autenticación y persistencia, comunicación con IPS externas mediante endpoints compatibles con flujos FHIR, cancelación mediante magic links, auditoría automática de operaciones y una entrada alternativa por NATS request/reply.

Dentro de la arquitectura general, este servicio actúa como capa de aplicación entre los clientes del sistema, la base de datos Supabase, los servicios externos de IPS y otros componentes del ecosistema Medix que consuman información de disponibilidad, citas o pacientes.

## Tecnologías utilizadas

- Lenguaje: Python 3.12
- Framework: FastAPI
- Servidor ASGI: Uvicorn
- Validación y configuración: Pydantic y pydantic-settings
- Base de datos y autenticación: Supabase
- Cliente HTTP: HTTPX
- Mensajería: NATS
- Pruebas: Pytest
- Contenedores: Docker y Docker Compose
- Gateway local: Traefik
- Documentación y pruebas manuales de API: Bruno

## Arquitectura del repositorio

```bash
/
├── app/
│   ├── api/
│   ├── clients/
│   ├── core/
│   ├── db/
│   ├── messaging/
│   ├── models/
│   ├── repositories/
│   ├── schemas/
│   ├── services/
│   ├── templates/
│   └── main.py
├── bruno-medix-appointments-api/
├── docs/
├── tests/
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── dynamic.yml
├── pytest.ini
├── requirements.txt
└── README.md
```

- `app/main.py`: punto de entrada de FastAPI; registra routers, middleware de auditoría y servidor NATS en el ciclo de vida de la aplicación.
- `app/api/`: contiene rutas HTTP, dependencias de autenticación, router principal y middlewares.
- `app/api/routes/`: define endpoints para autenticación, EPS, instituciones, pacientes, citas, consentimiento, recomendaciones, dispositivos, asistente y magic links.
- `app/clients/`: contiene clientes para comunicación HTTP con servicios externos.
- `app/core/`: centraliza la configuración leída desde variables de entorno.
- `app/db/`: configura el cliente de Supabase.
- `app/messaging/`: implementa contratos, handlers y servidor NATS request/reply.
- `app/repositories/`: encapsula el acceso a datos en Supabase.
- `app/schemas/`: define modelos Pydantic para requests y responses.
- `app/services/`: contiene la lógica de negocio del dominio.
- `app/templates/`: almacena plantillas HTML utilizadas por flujos como magic links.
- `bruno-medix-appointments-api/`: colección Bruno para probar endpoints de la API manualmente.
- `docs/`: documentación técnica complementaria sobre arquitectura y cambios.
- `tests/`: pruebas automatizadas de rutas, servicios, autenticación, NATS e integraciones simuladas.
- `Dockerfile`: definición de imagen Docker del servicio.
- `docker-compose.yml`: orquesta el servicio, NATS y Traefik para ejecución local o integrada.
- `dynamic.yml`: configuración dinámica usada por Traefik.
- `pytest.ini`: configuración de Pytest.
- `requirements.txt`: dependencias Python del proyecto.

## Requisitos previos

* Python 3.12 o superior
* pip
* Entorno virtual de Python
* Docker y Docker Compose, si se ejecuta mediante contenedores
* Supabase configurado para autenticación y persistencia
* Variables de entorno definidas en `.env`
* NATS, si se habilita la comunicación por mensajería
* Bruno, opcional para pruebas manuales de endpoints

La versión mínima exacta de Python debe ser validada por el equipo si se requiere compatibilidad fuera de Python 3.12, versión usada en el `Dockerfile`.

## Instalación

```bash
git clone <url-del-repositorio>
cd medix-appointments-api
```

Crear y activar un entorno virtual:

```bash
python3 -m venv venv
source venv/bin/activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Crear el archivo de variables de entorno:

```bash
cp .env.example .env
```

## Variables de entorno

El proyecto carga configuración desde `.env` mediante `pydantic-settings`. Ejemplo basado en `.env.example`:

```env
ENVIRONMENT=development
SUPABASE_URL=https://example.supabase.co
SUPABASE_KEY=replace-with-supabase-key
SUPABASE_SERVICE_ROLE_KEY=replace-with-service-role-key
JWT_SECRET=change-me
IPS_ROUTES_JSON={}
IPS_TIMEOUT_SECONDS=10
NATS_ENABLED=false
NATS_URL=nats://localhost:4222
NATS_SUBJECT_PREFIX=medix.appointments
NATS_QUEUE_GROUP=medix-api
NATS_CONNECT_TIMEOUT_SECONDS=2
NATS_CONNECT_MAX_ATTEMPTS=30
NATS_CONNECT_RETRY_DELAY_SECONDS=1
AI_SERVICE_URL=http://localhost:8000
```

- `ENVIRONMENT`: entorno de ejecución.
- `SUPABASE_URL`: URL del proyecto Supabase.
- `SUPABASE_KEY`: llave usada por la API para Supabase.
- `SUPABASE_SERVICE_ROLE_KEY`: llave service role para operaciones administrativas; si no se define, el código usa `SUPABASE_KEY` como respaldo.
- `JWT_SECRET`: secreto para firmar y validar magic links.
- `IPS_ROUTES_JSON`: mapa JSON de instituciones a URLs y llaves de IPS.
- `IPS_TIMEOUT_SECONDS`: tiempo máximo de espera para llamadas HTTP a IPS.
- `NATS_ENABLED`: habilita o deshabilita el servidor NATS.
- `NATS_URL`: URL del servidor NATS.
- `NATS_SUBJECT_PREFIX`: prefijo de subjects NATS.
- `NATS_QUEUE_GROUP`: grupo de cola NATS.
- `NATS_CONNECT_TIMEOUT_SECONDS`: timeout de conexión a NATS.
- `NATS_CONNECT_MAX_ATTEMPTS`: número máximo de intentos de conexión a NATS.
- `NATS_CONNECT_RETRY_DELAY_SECONDS`: tiempo entre reintentos de conexión a NATS.
- `AI_SERVICE_URL`: URL de servicio de IA usada por la configuración de gateway; su uso exacto debe ser validado por el equipo.

No se deben versionar credenciales reales en el repositorio.

## Ejecución local

Ejecutar la API en modo desarrollo:

```bash
uvicorn app.main:app --reload --port 8001
```

La documentación interactiva queda disponible en:

```text
http://localhost:8001/docs
http://localhost:8001/redoc
```

Ejecutar con Docker Compose:

```bash
docker compose up --build
```

Ejecutar con Docker:

```bash
docker build -t medix-api -f Dockerfile .
docker run --env-file .env -p 8001:8001 medix-api
```

El `docker-compose.yml` configura el servicio en el puerto `8001`, NATS en `4222` y Traefik como gateway. También define rutas de ejemplo en `IPS_ROUTES_JSON` para IPS simuladas o externas.

## Pruebas

Ejecutar pruebas automatizadas:

```bash
pytest
```

El repositorio incluye pruebas para rutas, servicios, autenticación, middleware de auditoría, NATS y comunicación con IPS simuladas.

## Uso general

La API expone endpoints REST para administrar catálogos, pacientes, citas y flujos complementarios del sistema Medix. La mayoría de endpoints bajo `/api/*` requiere el encabezado:

```http
Authorization: Bearer <token>
```

El token se valida contra Supabase y el usuario debe existir localmente con estado `ACTIVO`. Las rutas públicas o con mecanismos propios incluyen `/`, `/docs`, `/redoc`, `/openapi.json`, `/auth/*` y `/magic/*`.

Ejemplos generales de endpoints identificados:

```text
GET    /
GET    /auth/eligibility/{telefono}
GET    /api/eps/
GET    /api/eps/{id_eps}/ips
GET    /api/especialidades
GET    /api/instituciones/
GET    /api/instituciones/{id_institucion}/especialidades
GET    /api/instituciones/{id_institucion}/disponibilidad
GET    /api/instituciones/{id_institucion}/health
POST   /api/instituciones/{id_institucion}/citas/
GET    /api/instituciones/{id_institucion}/citas/
GET    /api/instituciones/{id_institucion}/citas/{id_cita}
PUT    /api/instituciones/{id_institucion}/citas/{id_cita}
DELETE /api/instituciones/{id_institucion}/citas/{id_cita}
GET    /api/pacientes/
POST   /api/pacientes/
GET    /api/pacientes/{id_paciente}
GET    /api/pacientes/{id_paciente}/profile
GET    /api/pacientes/{id_paciente}/citas
GET    /api/aceptacion-documento/activo
GET    /api/aceptacion-documento/estado
POST   /api/aceptacion-documento
GET    /api/recomendaciones/
POST   /api/recomendaciones/
POST   /api/dispositivos/token
GET    /magic/cancel-cita
```

El servicio también puede responder solicitudes por NATS cuando `NATS_ENABLED=true`. La lógica de negocio se comparte entre las rutas HTTP y los handlers NATS.

La auditoría automática intenta registrar operaciones bajo `/api/*` en `Log_Auditoria`. La política es fail-open: si falla el registro de auditoría, la API continúa respondiendo el flujo principal.

## Relación con otros repositorios

Este repositorio se relaciona con el ecosistema Medix como servicio backend de citas y catálogos médicos. Se comunica con:

* Supabase, para autenticación y persistencia.
* Servicios o simuladores de IPS, mediante endpoints FHIR o adaptadores HTTP.
* NATS, para integración por mensajería cuando esté habilitada.
* Gateway Traefik, para exposición integrada bajo rutas como `/appointments`.
* Posibles clientes frontend o asistentes que consuman disponibilidad, citas, pacientes y recomendaciones.

La relación exacta con otros repositorios de la organización debe ser documentada por el equipo de desarrollo.

## Estado del proyecto

En desarrollo.

El repositorio cuenta con estructura de API, Dockerfile, Docker Compose, colección Bruno, documentación técnica y pruebas automatizadas. El estado académico o de despliegue final debe ser confirmado por el equipo.

## Convenciones

Convenciones detectadas:

* Arquitectura por capas: routes, services, repositories, schemas, clients y messaging.
* Rutas HTTP del dominio agrupadas en `app/api/routes/`.
* Lógica de negocio concentrada en `app/services/`.
* Acceso a datos encapsulado en `app/repositories/`.
* Modelos de entrada y salida definidos con Pydantic en `app/schemas/`.
* Variables de entorno centralizadas en `.env.example` y `app/core/config.py`.
* Pruebas automatizadas ubicadas en `tests/` y ejecutadas con Pytest.

Convenciones recomendadas:

* Usar ramas descriptivas como `feature/nombre-funcionalidad`, `fix/nombre-error` o `docs/nombre-documentacion`.
* Escribir commits claros y accionables, preferiblemente siguiendo Conventional Commits, por ejemplo `feat: agregar endpoint de citas`.
* Mantener nuevas rutas sin lógica de negocio compleja; delegar reglas a servicios.
* No versionar credenciales reales ni archivos `.env` con información sensible.
* Ejecutar `pytest` antes de integrar cambios relevantes.
* Mantener nombres de carpetas y archivos en minúsculas y con responsabilidad clara.

## Autores

Proyecto desarrollado como parte del trabajo de grado.

Equipo de desarrollo:

* Adrián Eduardo Ruiz Cerquera
* Leonardo Velázquez Colin
* Diego Alejandro Jara Rojas
* Jairo Andrés Sierra Combariza

## Licencia

* CC BY-NC 4.0
