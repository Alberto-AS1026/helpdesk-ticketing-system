# Changelog

Todos los cambios relevantes del proyecto se documentan en este archivo.

Formato basado en [Keep a Changelog](https://keepachangelog.com/) y
versionado semántico (https://semver.org/).

## [Unreleased]

### Planned
- Núcleo de tickets: creación, asignación, estados, comentarios e historial.
- Autenticación con JWT y roles (usuario, técnico, administrador).
- Búsqueda, filtros y estadísticas.
- Frontend y dashboard.
- Dockerización completa del proyecto.

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
