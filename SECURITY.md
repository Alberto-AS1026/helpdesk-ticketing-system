# Seguridad

Resumen de las medidas de seguridad del proyecto, sus límites conocidos y la
deuda técnica pendiente. Es un proyecto de portfolio y laboratorio: no está
pensado para exponerse a Internet sin las mejoras indicadas al final.

## Autenticación

- Login con `POST /auth/login` (email y contraseña).
- Las contraseñas **nunca se guardan en claro**: se almacena un hash **bcrypt**
  con salt aleatorio por usuario. La API jamás devuelve `password_hash`.
- Longitud de contraseña: mínimo 8 y máximo 72 caracteres (bcrypt solo procesa
  los primeros 72 bytes, así se evitan truncados silenciosos).
- Tras un login correcto se emite un **JWT** firmado (HS256) con caducidad de
  60 minutos. Contiene solo el id del usuario (`sub`), la fecha de emisión y la
  de caducidad. Está firmado, **no cifrado**: nunca se guardan datos sensibles
  dentro.
- Al decodificar se fuerza el algoritmo esperado y se comprueban firma y
  caducidad.
- El rol y el estado del usuario se leen de la base de datos en cada petición,
  no del token: desactivar a un usuario o cambiar su rol tiene efecto inmediato.
- Mensaje de error genérico ("Email o contraseña incorrectos") y comparación
  con un hash ficticio cuando el email no existe, para no revelar qué cuentas
  existen (enumeración de usuarios).

## Autorización (roles)

| Recurso | Leer | Escribir |
|---|---|---|
| Departamentos, categorías, prioridades | Todos los autenticados | Administrador |
| Usuarios y técnicos | Técnico y administrador | Administrador |
| Equipos | Todos los autenticados | Técnico y administrador |
| Tickets | Usuario: solo los suyos. Técnico y administrador: todos | Crear: todos. Asignar, cambiar estado y registrar diagnóstico o solución: técnico y administrador |

- Solo un administrador puede crear usuarios y asignar roles, por lo que nadie
  puede auto-asignarse el rol `admin`.
- **Autorización a nivel de objeto:** un usuario normal que pide un ticket
  ajeno recibe `404` (no `403`), para no confirmar que existe.
- La identidad (creador, autor de comentario, autor de cambio) se toma
  **siempre del token**, nunca del cuerpo de la petición.
- La política de permisos está centralizada en `backend/app/main.py`.

## Protección frente a ataques

| Medida | Detalle |
|---|---|
| Fuerza bruta | 5 fallos de login en 15 minutos bloquean con `429` y `Retry-After`. La clave es IP + email, para que un atacante no pueda bloquear a un usuario legítimo desde otra IP. |
| Inyección SQL | Todo el acceso a datos usa SQLAlchemy con parámetros; no se construye SQL con texto del usuario. |
| Validación de entrada | Pydantic valida tipos, longitudes, rangos y valores permitidos (`422`). La base de datos añade `CHECK`, `UNIQUE` y claves foráneas como segunda barrera. |
| CORS | Lista blanca de orígenes en `CORS_ORIGINS`. Nunca `*`. Sin cookies (token en cabecera), por lo que `allow_credentials` está desactivado. |
| Cabeceras | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`. |
| Inyección de logs | Los datos del usuario se registran con `%r`, que escapa saltos de línea. |

## Secretos y configuración

- `SECRET_KEY` y las credenciales de base de datos viven en `.env`, que está en
  `.gitignore`. `.env.example` solo contiene valores de ejemplo.
- La aplicación no arranca si `SECRET_KEY` falta o tiene menos de 32 caracteres.
- Generar una clave: `openssl rand -hex 32`.
- Si se cambia `SECRET_KEY`, todos los tokens existentes dejan de ser válidos.
- Si una clave se expone, hay que rotarla de inmediato.

## Registro de eventos

El logger `helpdesk.security` registra logins correctos, fallidos y bloqueados,
tokens no válidos y accesos denegados (`403`), con IP o id de usuario.
**Nunca** se registran contraseñas ni tokens. Los logs rotan al llegar a 1 MB
y no se versionan.

## Datos de laboratorio

- Los usuarios `@empresa.test` del seed tienen una contraseña de desarrollo
  conocida, asignada con `scripts/set_dev_passwords.py`. **Solo para
  laboratorio.** En un entorno real las contraseñas iniciales no se versionan:
  se generan aleatorias y se obliga a cambiarlas en el primer acceso.

## Limitaciones conocidas

- El contador de intentos de login está en **memoria**: se pierde al reiniciar y
  no se comparte entre procesos. En producción: Redis o Nginx.
- No hay **revocación de tokens** ni *refresh tokens*: un token robado es válido
  hasta que caduca (60 minutos), salvo que se desactive al usuario.
- La API habla **HTTP plano**. Se necesita HTTPS (TLS) en un proxy inverso antes
  de exponerla.
- No hay `Content-Security-Policy` en la API; se añadirá en Nginx para el
  frontend.
- No hay endpoint para que el usuario cambie su propia contraseña ni flujo de
  recuperación.
- No hay autenticación de doble factor.
- PostgreSQL publica el puerto 5432 en el host para desarrollo. En la
  dockerización se restringirá a la red interna de Docker.

## Mejoras previstas

1. Nginx con HTTPS y `Content-Security-Policy`.
2. Puerto de PostgreSQL solo en la red interna de Docker.
3. Endpoint de cambio de contraseña y política de contraseñas iniciales.
4. Límite de intentos persistente.
5. Tests automáticos de permisos (Fase 8).

## Cómo informar de un problema

Abre un *issue* en el repositorio. Si el problema es una vulnerabilidad, no
incluyas datos sensibles ni tokens reales en el texto.
