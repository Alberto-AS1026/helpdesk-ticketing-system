# Changelog

Todos los cambios relevantes del proyecto se documentan en este archivo.

Formato basado en [Keep a Changelog](https://keepachangelog.com/) y
versionado semántico (https://semver.org/).

## [Unreleased]

### Added
- Dockerización completa: `docker-compose.yml` con PostgreSQL, API y Nginx.
- Carga automática del esquema, seed e índices al crear el volumen de PostgreSQL.
- `database/05_dev_passwords.sql`: contraseña de laboratorio para los usuarios del seed.
- `nginx/helpdesk.docker.conf` y healthchecks en `db` y `api`.
- README completo: capturas, prueba guiada, diagramas (arquitectura, estados, chat y modelo de datos), API, configuración, tests y limitaciones.
- Chat 1 a 1 entre usuarios y personal técnico (`/chat`, `chat.html`) con interfaz de app de mensajería: avatares, buscador, burbujas agrupadas, separadores de día, checks de enviado/entregado/leído, «en línea» / «últ. vez», «escribiendo…», emojis, enlaces a tickets (`#12`) y vista móvil de un panel.
- Contador de no leídos en la barra superior y botón «Chatear con…» en el detalle del ticket.
- Tiempo real con WebSocket (`/chat/ws`): mensajes, leído, «escribiendo…» y presencia al instante; contador de la barra superior actualizado en todas las páginas; reconexión automática y vuelta al polling si el WebSocket no está disponible. Nginx configurado para WebSocket y CSP `connect-src` ampliada.
- Endpoints `/chat/conversations/{id}/sync` (todo lo que necesita la conversación abierta en una sola llamada) y `/chat/conversations/{id}/typing`.
- `database/06_chat.sql` (tablas `chat_conversations`, `chat_messages` y `chat_presence`; se puede reaplicar) y 31 tests del chat (10 de WebSocket).
- `technician_user_id` en la respuesta de los tickets.
- Modo oscuro/claro con botón junto a «Salir» (a su izquierda) y también en la página de login; se recuerda la elección y, por defecto, sigue al sistema.

### Changed
- El login no distingue mayúsculas en el email.
- Estados de ticket con código de color: rojo (Abierto), amarillo (En progreso, Pendiente) y verde (Resuelto, Cerrado), también en el gráfico del dashboard.
- La barra superior muestra solo el nombre del usuario, sin el rol.
- El botón «Salir» pasa a ser un icono.
- Barra de navegación igual en todas las páginas.
- Nginx (Docker) resuelve la API por DNS en cada petición, para no dar `502` si el contenedor se recrea.

### Fixed
- `requirements-dev.txt` no incluía `pytest`, `httpx` ni las dependencias de la app (el CI no podía instalar el entorno).
- Caso duplicado y numeración de `TROUBLESHOOTING.md`.
- Las etiquetas de estado ya no se parten en dos líneas en el listado.
- Nginx envía `Cache-Control: no-cache`: el navegador ya no mezcla archivos JS antiguos de su caché con los nuevos tras una actualización (rompía el chat en Firefox).

### Security
- PostgreSQL y la API ya no publican puertos en el host: solo Nginx es accesible.
- La API solo confía en `X-Forwarded-For` si viene de la IP fija de Nginx (antes `*`, que permitía falsear la IP y saltarse el límite de login).
- Nginx sobrescribe `X-Forwarded-For` en lugar de añadir al valor del cliente.

## [0.1.0] - 2026-10-07

### Added
- Esquema PostgreSQL con 9 tablas, claves primarias y foráneas, constraints e índices.
- Datos de prueba (seed) para desarrollo.
- PostgreSQL 16 en Docker Compose con volumen persistente.
- API con FastAPI y endpoints de salud (`/health`, `/health/db`).
- CRUD de departamentos, categorías, prioridades, usuarios, técnicos y equipos.
- Hash de contraseñas con bcrypt; las respuestas nunca incluyen `password_hash`.
- Validación de datos con Pydantic (códigos 404, 409 y 422).

## [0.2.0] - 2026-10-10

### Added
- Tickets: creación, consulta y listado con nombres de prioridad, categoría, creador y técnico.
- Asignación de técnicos y máquina de estados con reglas de negocio.
- Registro de diagnóstico y solución; cálculo de `resolved_at` y `resolution_minutes`.
- Comentarios por ticket (no editables, orden cronológico).
- Historial automático de cambios (auditoría) en la misma transacción.

## [0.3.0] - 2026-10-11

### Added
- Login con JWT (`/auth/login`, `/auth/me`) y contraseñas con hash bcrypt.
- Roles (usuario, técnico, administrador) con política de permisos por router.
- Visibilidad de tickets por rol: un usuario normal solo ve y comenta los suyos.
- Límite de intentos de login (`429` con `Retry-After`).
- CORS con lista blanca de orígenes y cabeceras de seguridad.
- Logging con rotación y registro de eventos de seguridad.
- `SECURITY.md` y guía `TROUBLESHOOTING.md` con casos reales.

### Changed
- La identidad (creador, autor, responsable del cambio) se toma del token:
  `created_by`, `author_id` y `changed_by` ya no se aceptan en las peticiones.
- Solo el administrador puede crear usuarios y asignar roles.

### Security
- Cerrado el agujero que permitía a cualquiera crear usuarios `admin`.
- `UserOut.email` pasa a `str` en la respuesta (la validación estricta se
  mantiene al crear y modificar usuarios).

## [0.4.0] - 2026-10-11

### Added
- Búsqueda de tickets por texto, con filtros por estado, prioridad, categoría, técnico y fechas.
- Ordenación (lista blanca) y paginación con total.
- Índices `pg_trgm` (GIN) y compuesto para la bandeja del técnico.
- Datos de volumen (50.000 tickets) y mediciones con `EXPLAIN ANALYZE`.
- Endpoint `/stats` (técnico y admin): resumen, tickets por estado, prioridad y categoría, carga por técnico y tickets por día.

### Changed
- `GET /tickets` devuelve `{total, limit, offset, items}` en lugar de una lista (cambio incompatible).

## [0.5.0] - 2026-10-12

### Added
- Frontend en HTML, CSS y JavaScript sin frameworks, servido por Nginx.
- Login, listado de tickets con búsqueda, filtros, ordenación y paginación.
- Detalle de ticket con comentarios, historial y acciones del personal técnico.
- Formulario de nuevo ticket.
- Dashboard con Chart.js (KPIs y cinco gráficos) alimentado por `/stats`.
- Nginx como proxy inverso (`/api`) con `Content-Security-Policy` estricta.

### Security
- Renderizado con `textContent` para evitar XSS; sin `unsafe-inline` en scripts.
- Chart.js servido localmente; sin dependencias de CDN.
- IP real del cliente tras Nginx para el límite de intentos de login.

## [0.6.0] - 2026-10-13

### Added
- Suite de 99 tests con pytest sobre una base de datos aislada `helpdesk_test`.
- Tests de autenticación, flujo y reglas de tickets, visibilidad por rol, historial, CRUD, matriz de permisos, búsqueda y estadísticas.
- Cobertura del 92 % medida con pytest-cov.
- Integración continua con GitHub Actions y PostgreSQL como service container.
- Protección de `main`: PR obligatorio y check `pytest` en verde.
