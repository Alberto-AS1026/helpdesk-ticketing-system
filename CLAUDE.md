# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Help desk de tickets con chat en tiempo real. Backend FastAPI + SQLAlchemy 2 + PostgreSQL 16; frontend HTML/CSS/JS nativo (sin frameworks, sin build, sin CDNs); todo orquestado con Docker Compose detrás de Nginx. El código, los comentarios, los mensajes de error de la API y la documentación están en **español**: mantén ese idioma.

## Comandos

```bash
# Levantar la pila (necesita .env con DB_PASSWORD y SECRET_KEY >= 32 caracteres)
docker compose up -d --build
docker compose ps                       # db y api deben estar "healthy"
docker compose logs -f api
docker compose down -v && docker compose up -d   # reset completo de la base (reaplica los SQL)
```

La web queda en http://localhost:8080 (Nginx). La API no publica puerto: se llega por `/api/*`. Usuarios del seed (5): `administrador`, `tecnicoA`, `tecnicoB`, `empleadoA`, `empleadoB` `@empresa.test`; contraseña = nombre sin espacios + `Help2026` (p. ej. `TecnicoAHelp2026`).

### Tests

Los tests usan una PostgreSQL real (no SQLite ni mocks). `conftest.py` exige `TEST_DATABASE_URL` cuyo nombre de base termine en `_test` y **vacía todas las tablas (TRUNCATE) antes de cada test**, insertando datos mínimos propios (admin, tech1, user1, user2 con contraseña `Test_Password_1`). La base de test solo lleva `01_schema.sql`, `04_indexes.sql` y `06_chat.sql` (sin seed).

Con `TEST_DATABASE_URL` y `SECRET_KEY` en el entorno (o en el `.env` de la raíz), desde `backend/`:

```bash
python -m pytest --cov=app -q
python -m pytest tests/test_tickets_rules.py -q          # un fichero
python -m pytest tests/test_chat.py::test_nombre -q      # un test
```

Si solo está la pila de Docker (la base no tiene puerto publicado), sigue la sección "Tests" de `backend/README.md`: crear `helpdesk_test`, cargar los tres SQL y ejecutar pytest en un contenedor `python:3.13-slim` conectado a la red `helpdesk-ticketing-system_backend`. CI (`.github/workflows/tests.yml`) hace lo mismo con un service container de Postgres.

No hay linter configurado.

## Arquitectura

### Esquema de base de datos: SQL primero, sin migraciones
No hay Alembic ni `create_all`. El esquema real está en `database/*.sql` y `app/models.py` lo **refleja a mano**. Cualquier cambio de esquema hay que hacerlo en ambos sitios, y además en los `TABLES` del `TRUNCATE` de `tests/conftest.py` si es una tabla nueva. Los SQL se montan en `docker-entrypoint-initdb.d` y solo se ejecutan cuando el volumen `pgdata` está vacío; `06_chat.sql` es idempotente y se puede reaplicar sobre una base existente. `03_bulk_test_data.sql` no se monta (es opcional, manual).

### Permisos centralizados en `app/main.py`
Cada router se incluye con `protect(read=..., write=...)` (`app/dependencies.py`): un conjunto de roles para GET/HEAD/OPTIONS y otro para el resto de métodos. Roles: `user`, `technician`, `admin` (grupos `ALL_ROLES`, `STAFF`, `ADMIN_ONLY`). Las restricciones más finas (p. ej. que solo STAFF asigne o resuelva) van dentro de los routers con `require_roles(...)`. `tests/test_permissions.py` cubre la matriz completa: si cambias permisos, actualízalo.

Reglas que se repiten por todo el código:
- Un `user` que pide un ticket o conversación ajena recibe **404, no 403** (`get_visible` en `routers/tickets.py`), para no revelar que existe. Las conversaciones ajenas no las lee ni el admin.
- La identidad (creador, autor, quién hizo el cambio) sale **siempre del token**, nunca del body.
- En los listados, el filtro por rol se aplica antes que cualquier otro filtro.

### Flujo de tickets (`routers/tickets.py`)
Las transiciones de estado están en `ALLOWED_TRANSITIONS` (estados en español: `Abierto`, `En progreso`, `Pendiente`, `Resuelto`, `Cerrado`; también en un `CHECK` del SQL y en el regex del filtro). Transición no permitida → `409`; pasar a `Resuelto` sin diagnóstico y solución → `422`; no se trabaja sin técnico asignado. Cada cambio se registra en `ticket_history` con `log_change()` **en la misma transacción** que el cambio.

### Chat y tiempo real
- Escribir y leer mensajes va **por REST** (`routers/chat.py`, con sus permisos). El WebSocket `/chat/ws` (`chat.ws_router`, incluido sin `protect`) solo **avisa**: mensajes nuevos, leídos, "escribiendo…" y presencia.
- El WS se autentica con el **primer mensaje** `{"type":"auth","token":...}`, nunca en la URL; token inválido → cierre `4401`.
- `app/realtime.py` (`ConnectionManager`) guarda los sockets **en memoria**. Los endpoints REST son síncronos (pool de hilos) y llaman a `manager.notify()`, que programa el envío en el event loop con `run_coroutine_threadsafe`. Por eso la API debe correr en **un único proceso uvicorn** (sin `--workers`).
- El frontend (`frontend/js/chat.js`) reconecta con backoff y, mientras tanto, hace polling cada 2,5 s; al reconectar recupera con `/sync?after_id=`.

### Frontend
Páginas HTML estáticas que cargan scripts clásicos (no módulos) en orden: `theme.js` (en `<head>`) → `api.js` → `layout.js` → script de la página. Todos comparten el ámbito global, así que **no repitas nombres de nivel superior** entre ellos (un `const` duplicado rompe la página). `api.js` define las utilidades globales (`apiFetch`, `requireLogin`, `el`, `ticketNumber`/`parseTicketNumber` para el formato `INC0000001`, `priorityTag`, `ROLE_LABELS`; sesión en `sessionStorage`, un 401 hace logout). `layout.js` construye por DOM la cabecera (buscador global, usuario, tema, salir) y el menú lateral, y envuelve el `<main>` de la página; los HTML privados solo contienen su `<main>`. El menú usa `?view=` en `/` (`mine`, `assigned`, `unassigned`, `open`, `progress`, `pending`, `resolved`, `all`), que interpreta `tickets.js`. La estética imita una consola ITSM (tipo ServiceNow); `login.html` no usa `layout.js`. Nginx impone una CSP estricta sin `unsafe-inline`: nada de `<script>`/`style` inline ni recursos externos (Chart.js está en `js/vendor/`). Pinta el contenido siempre con `textContent`, nunca con `innerHTML`.

### Nginx y red
`nginx/helpdesk.docker.conf` es el de Docker (sirve `frontend/`, proxy de `/api/` y de `/api/chat/ws` con upgrade de WebSocket, cabeceras de seguridad y CSP); `nginx/helpdesk.conf` es para una instalación directa en servidor. Si cambias rutas o cabeceras, revisa los dos. Nginx tiene IP fija `172.28.0.10` y la API solo confía en `X-Forwarded-For` de esa IP (`FORWARDED_ALLOW_IPS`), lo que hace fiable el límite de intentos de login por IP (`app/ratelimit.py`, en memoria).

### Configuración
`app/config.py` y `app/database.py` cargan el `.env` de la **raíz del repo** y fallan al importar si faltan `SECRET_KEY` (>= 32 caracteres) o `DATABASE_URL`. Por eso `conftest.py` fija `DATABASE_URL = TEST_DATABASE_URL` antes de importar la app.

## Documentación relacionada
- `docs/TROUBLESHOOTING.md`: problemas reales del desarrollo (síntoma, diagnóstico, solución). Consúltalo ante fallos de Docker, Nginx, WebSocket o tests.
- `SECURITY.md`: medidas y matriz de permisos. `CHANGELOG.md`: se mantiene al día en la sección `[Unreleased]` (formato Keep a Changelog).
