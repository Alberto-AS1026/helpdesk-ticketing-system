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
