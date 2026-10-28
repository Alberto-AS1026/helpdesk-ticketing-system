# Help Desk Ticketing System

Sistema de tickets de soporte técnico: los usuarios abren incidencias, los
técnicos las asignan, diagnostican y resuelven, y el administrador gestiona
usuarios, técnicos y catálogos. Incluye historial de cambios, comentarios,
búsqueda con filtros, un dashboard de estadísticas y un chat entre usuarios y
técnicos para intentar resolver las incidencias en remoto antes de ir en persona.

## Stack

| Capa | Tecnología |
|---|---|
| Base de datos | PostgreSQL 16 |
| API | FastAPI + SQLAlchemy 2, JWT (PyJWT), bcrypt |
| Frontend | HTML + JavaScript sin frameworks, Chart.js |
| Proxy / estáticos | Nginx |
| Contenedores | Docker Compose |
| Tests / CI | pytest + GitHub Actions |

## Arquitectura en Docker

```
navegador ──► web (Nginx :8080) ──► /              frontend estático
                                 ├─► /api/*         api (FastAPI :8000) ──► db (PostgreSQL :5432)
                                 └─► /api/chat/ws   WebSocket del chat (misma API)
```

Solo el servicio `web` publica un puerto en el host. La API y PostgreSQL
viven en la red interna `backend` y no son accesibles desde fuera.

## Puesta en marcha

Requisitos: Docker y Docker Compose v2.

```bash
cp .env.example .env
# Edita .env: pon una DB_PASSWORD propia y una SECRET_KEY nueva
openssl rand -hex 32          # sirve para SECRET_KEY

docker compose up -d --build
docker compose ps             # los tres servicios deben salir "healthy" / "running"
```

Abre <http://localhost:8080>.

La primera vez que arranca, el contenedor de PostgreSQL carga en orden
`01_schema.sql`, `02_seed.sql`, `04_indexes.sql`, `05_dev_passwords.sql` y
`06_chat.sql`.
Esto solo ocurre con el volumen vacío; para empezar de cero:

```bash
docker compose down -v        # borra también los datos
docker compose up -d
```

Si tu base de datos ya existía antes de añadir el chat, crea sus tablas con:

```bash
docker compose exec -T db psql -U helpdesk_user -d helpdesk < database/06_chat.sql
```

### Usuarios de prueba

Todos tienen la contraseña de laboratorio `Helpdesk_2026`. **Solo para
desarrollo.**

| Email | Rol |
|---|---|
| `admin@empresa.test` | admin |
| `pablo@empresa.test`, `ana@empresa.test` | technician |
| `laura@empresa.test`, `carlos@empresa.test`, `marta@empresa.test` | user |

### Datos de volumen (opcional)

```bash
docker compose exec -T db psql -U helpdesk_user -d helpdesk < database/03_bulk_test_data.sql
```

Genera 50 000 tickets `BULK-` para probar el rendimiento de búsquedas y del
dashboard.

## Chat

Interfaz al estilo de las apps de mensajería:

- Lista de chats con avatar, buscador, último mensaje, hora y no leídos;
  botón ✎ para empezar un chat nuevo con cualquier contacto permitido.
- Burbujas agrupadas, separadores de día y enlaces automáticos a tickets (`#12`).
- Checks de estado: ✓ enviado, ✓✓ entregado y ✓✓ azul leído.
- "en línea", "últ. vez hoy a las…" y "escribiendo…" en la cabecera.
- Emojis, caja de texto que crece, Intro para enviar y Mayús+Intro para salto
  de línea, y botón ↓ con los mensajes nuevos si estás leyendo más arriba.
- En móvil se ve un panel cada vez (lista o conversación).
- Enlace **Chat** en la barra superior con el número de mensajes sin leer, y
  botón **Chatear con…** en el detalle de cada ticket.

**Tiempo real con WebSocket** (`/api/chat/ws`, a través de Nginx): los
mensajes, los checks de leído, el "escribiendo…" y las conexiones y
desconexiones llegan al instante, y el contador de "Chat" de la barra superior
se actualiza en todas las páginas. Si el WebSocket no está disponible (red,
proxy, navegador), la página vuelve sola a consultar cada 2,5 segundos y
reintenta la conexión con espera creciente.

La API debe ejecutarse con **un solo proceso** de uvicorn, como en el
Dockerfile: las conexiones se registran en memoria. Para escalar a varios
procesos o réplicas habría que repartir los avisos con PostgreSQL
`LISTEN/NOTIFY`.

## Comandos útiles

```bash
docker compose logs -f api                       # logs de la API
docker compose exec api tail -f logs/helpdesk.log # log de seguridad
docker compose exec db psql -U helpdesk_user -d helpdesk
curl http://localhost:8080/api/health/db
```

## Tests

Los tests necesitan una base cuyo nombre termine en `_test` (el `conftest.py`
se niega a arrancar en otro caso, porque hace `TRUNCATE`).

Con la pila de Docker en marcha:

```bash
docker compose exec db createdb -U helpdesk_user helpdesk_test
docker compose exec -T db psql -U helpdesk_user -d helpdesk_test < database/01_schema.sql
docker compose exec -T db psql -U helpdesk_user -d helpdesk_test < database/04_indexes.sql
docker compose exec -T db psql -U helpdesk_user -d helpdesk_test < database/06_chat.sql

docker run --rm --network helpdesk-ticketing-system_backend \
  -v "$PWD/backend:/src:ro" \
  -e TEST_DATABASE_URL=postgresql://helpdesk_user:<DB_PASSWORD>@db:5432/helpdesk_test \
  -e SECRET_KEY=clave-solo-para-tests-0123456789abcdef0123456789 \
  python:3.13-slim sh -c "cp -r /src /srv/b && cd /srv/b \
    && pip install -q -r requirements-dev.txt \
    && python -m pytest --cov=app -q -p no:cacheprovider"
```

En GitHub Actions se ejecutan en cada push y pull request a `main`
(`.github/workflows/tests.yml`).

## Estructura

```
backend/      API FastAPI (app/), tests/ y scripts/
frontend/     HTML, CSS y JS servidos por Nginx
database/     Scripts SQL de esquema, datos e índices
nginx/        helpdesk.conf (instalación directa) y helpdesk.docker.conf (Compose)
docs/         TROUBLESHOOTING.md
```

## Más información

- [SECURITY.md](SECURITY.md): medidas de seguridad y limitaciones conocidas.
- [CHANGELOG.md](CHANGELOG.md): historial de versiones.
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md): problemas reales y cómo se resolvieron.
