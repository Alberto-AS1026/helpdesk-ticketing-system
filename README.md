# Help Desk Ticketing System

[![Tests](https://github.com/Alberto-AS1026/helpdesk-ticketing-system/actions/workflows/tests.yml/badge.svg)](https://github.com/Alberto-AS1026/helpdesk-ticketing-system/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)

Cuando a alguien de una empresa se le estropea el ordenador, no le funciona
la impresora o se queda sin acceso al correo, lo normal es que avise al
departamento de informática. Si ese aviso llega por un pasillo, por teléfono
o por un correo suelto, es fácil que se pierda, que nadie sepa quién se está
encargando o que, semanas después, no quede rastro de cómo se solucionó.

Este proyecto es una **aplicación de soporte técnico (help desk)** pensada
para poner orden en ese proceso:

- **Los empleados** abren un incidente contando qué les pasa y pueden seguir
  en todo momento en qué punto está.
- **Los técnicos** ven la cola de trabajo, se asignan los incidentes, anotan
  lo que van haciendo y los resuelven dejando escrito el diagnóstico y la
  solución.
- **El administrador** lo supervisa todo desde un panel con indicadores y
  gráficos.

Además incluye un **chat en tiempo real**: muchas incidencias se arreglan con
dos preguntas y una indicación ("¿has probado a reconectar el cable?"), así
que el técnico puede intentar resolverlas en remoto antes de desplazarse al
puesto.

La interfaz imita a las herramientas profesionales de gestión de servicios
(tipo ServiceNow): cada incidente tiene un número como `INC0000001`, hay un
menú lateral con las distintas colas de trabajo y la ficha de cada incidente
muestra su recorrido de estados y toda su actividad.

## Pruébalo en tu ordenador

Solo necesitas **Docker** con **Docker Compose v2**.

```bash
git clone https://github.com/Alberto-AS1026/helpdesk-ticketing-system.git
cd helpdesk-ticketing-system

cp .env.example .env
# Abre .env y pon una DB_PASSWORD propia y una SECRET_KEY nueva.
# Puedes generar la clave con:
openssl rand -hex 32

docker compose up -d --build
docker compose ps        # "db" y "api" deben aparecer como "healthy"
```

Después abre **<http://localhost:8080>**. La primera vez, la base de datos se
crea sola y se rellena con unos cuantos incidentes de ejemplo. Si en algún
momento quieres volver a empezar desde cero:
`docker compose down -v && docker compose up -d`.

### Usuarios de prueba

Hay cinco usuarios preparados. La contraseña de cada uno es su nombre sin
espacios seguido de `Help2026` (solo para desarrollo).

| Quién | Email | Contraseña |
|---|---|---|
| Administrador | `administrador@empresa.test` | `AdministradorHelp2026` |
| Técnico | `tecnicoA@empresa.test` | `TecnicoAHelp2026` |
| Técnico | `tecnicoB@empresa.test` | `TecnicoBHelp2026` |
| Empleado | `empleadoA@empresa.test` | `EmpleadoAHelp2026` |
| Empleado | `empleadoB@empresa.test` | `EmpleadoBHelp2026` |

Un consejo: abre una ventana normal y otra de incógnito, entra con un
empleado en una y con un técnico en la otra, y verás cómo se comunican.
La [guía de uso](docs/GUIA-DE-USO.md) propone un recorrido de cinco minutos.

## Con qué está hecho

- **Backend:** Python con FastAPI, SQLAlchemy y Pydantic. Autenticación con
  JWT y contraseñas cifradas con bcrypt.
- **Base de datos:** PostgreSQL 16.
- **Frontend:** HTML, CSS y JavaScript sin frameworks. Funciona en el móvil
  y tiene modo claro y oscuro.
- **Infraestructura:** Docker Compose y Nginx, que sirve la web y hace de
  puerta de entrada a la API.
- **Calidad:** 130 tests automáticos (92 % de cobertura) que GitHub Actions
  ejecuta en cada cambio.

## Dónde está cada cosa

La documentación está repartida según lo que quieras saber:

| Si quieres… | Lee |
|---|---|
| Saber cómo se usa la aplicación y qué puede hacer cada persona | [Guía de uso](docs/GUIA-DE-USO.md) |
| Entender cómo encajan las piezas, la seguridad y los límites del proyecto | [Arquitectura](docs/ARQUITECTURA.md) |
| Conocer la API, las reglas de negocio, el chat por dentro o ejecutar los tests | [backend/README.md](backend/README.md) |
| Ver cómo está construida la interfaz | [frontend/README.md](frontend/README.md) |
| Consultar el modelo de datos y los scripts SQL | [database/README.md](database/README.md) |
| Revisar las medidas de seguridad en detalle | [SECURITY.md](SECURITY.md) |
| Leer los problemas reales que surgieron y cómo se resolvieron | [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) |
| Ver qué ha cambiado en cada versión | [CHANGELOG.md](CHANGELOG.md) |

## Antes de usarlo en serio

Es un proyecto de **portfolio y laboratorio**: está pensado para aprender y
enseñar cómo se construye una aplicación así, no para exponerse a Internet
tal cual. Faltarían, entre otras cosas, HTTPS, un sistema para que cada
persona gestione su propia contraseña y alguna pieza más para poder escalar.
Están todas explicadas en la [arquitectura](docs/ARQUITECTURA.md#lo-que-falta-para-producción).
