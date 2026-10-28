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
| Chat | Solo los dos participantes de cada conversación (ni siquiera el administrador lee chats ajenos) | Usuario: solo con técnicos y administradores. Técnico y administrador: con cualquier usuario activo |

- Solo un administrador puede crear usuarios y asignar roles, por lo que nadie
  puede auto-asignarse el rol `admin`.
- **Autorización a nivel de objeto:** un usuario normal que pide un ticket
  ajeno recibe `404` (no `403`), para no confirmar que existe.
- La identidad (creador, autor de comentario, autor de cambio) se toma
  **siempre del token**, nunca del cuerpo de la petición.
- La política de permisos está centralizada en `backend/app/main.py`.
- **Chat:** quien no participa en una conversación recibe `404`. La lista de
  contactos no incluye emails. No se puede escribir a un usuario desactivado,
  aunque el historial se conserva. Los mensajes se pintan con `textContent`
  (los enlaces `#12` se crean como nodos, sin `innerHTML`).
- **WebSocket del chat:** el token se envía en el primer mensaje, nunca en la
  URL (no queda en los logs de Nginx). Sin autenticar en 10 s, con un token no
  válido o al caducar el JWT, el servidor cierra con el código `4401`. Como no
  se usan cookies, otra web no puede abrir un socket en nombre del usuario.
  Máximo 10 conexiones por usuario, mensajes del cliente de hasta 4 KB y cierre
  tras 60 s sin actividad. El canal solo envía avisos: escribir y leer siguen
  pasando por la API REST, con sus permisos y validaciones.
- **Presencia:** cualquier usuario con el que puedes chatear ve si estás "en
  línea" y tu última conexión. Se registra con la actividad en la aplicación,
  como mucho una escritura cada 10 segundos por usuario.

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

## Docker

- Solo el servicio `web` (Nginx) publica un puerto en el host. La API y
  PostgreSQL están en la red interna `backend`.
- Nginx tiene una IP fija en esa red y la API solo acepta `X-Forwarded-For`
  desde ella (`FORWARDED_ALLOW_IPS`). Nginx sobrescribe la cabecera con la IP
  real del cliente, así que no se puede falsear para saltarse el límite de login.
- La API corre con un usuario sin privilegios (`appuser`, uid 1001).
- `docker compose` no arranca si faltan `DB_PASSWORD` o `SECRET_KEY` en `.env`.

## Registro de eventos

El logger `helpdesk.security` registra logins correctos, fallidos y bloqueados,
tokens no válidos y accesos denegados (`403`), con IP o id de usuario.
**Nunca** se registran contraseñas ni tokens. Los logs rotan al llegar a 1 MB
y no se versionan.

## Datos de laboratorio

- Los usuarios `@empresa.test` del seed tienen una contraseña de desarrollo
  conocida, asignada con `scripts/set_dev_passwords.py` o, en Docker, con
  `database/05_dev_passwords.sql`. **Solo para
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
- Los WebSockets se registran en memoria: un solo proceso de uvicorn.
- El chat no tiene límite de mensajes por minuto: un usuario podría saturar una
  conversación. Los mensajes no se cifran en la base de datos ni caducan.

## Mejoras previstas

1. HTTPS (TLS) en Nginx.
2. Endpoint de cambio de contraseña y política de contraseñas iniciales.
3. Límite de intentos persistente.

## Cómo informar de un problema

Abre un *issue* en el repositorio. Si el problema es una vulnerabilidad, no
incluyas datos sensibles ni tokens reales en el texto.
