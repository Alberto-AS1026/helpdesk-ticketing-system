# Troubleshooting

Registro de problemas reales encontrados durante el desarrollo del proyecto.
Cada caso sigue el mismo método: **síntoma, hipótesis, comprobaciones,
diagnóstico, solución y prevención**.

## Método general

1. **Leer el mensaje completo.** La causa suele estar en la última línea del error.
2. **Distinguir el origen:** ¿es local, de mi código o de un proveedor externo?
3. **Formular hipótesis** y ordenarlas de más a menos probable.
4. **Comprobar con comandos de solo lectura** antes de cambiar nada.
5. **Cambiar una sola cosa cada vez** y volver a probar.
6. **Documentar** el caso.

## Índice

| Área | Casos |
|---|---|
| Sistema y SSH | 1, 2 |
| Docker y PostgreSQL | 3, 4, 5 |
| Python y entorno | 6, 7, 8, 9 |
| API y errores HTTP | 10, 11, 12, 13, 14 |
| Git y GitHub | 15, 16, 17, 18, 19, 24 |
| Edición de archivos | 20, 21 |
| Terminal y shell | 22, 23 |

---

# Sistema y SSH

## 1. El servicio SSH no existe

**Síntoma:** `systemctl status ssh` responde `Unit ssh.service could not be found`.

**Hipótesis:** (1) no se instaló OpenSSH durante la instalación de Ubuntu; (2) el servicio tiene otro nombre.

**Comprobaciones:**
```bash
dpkg -l | grep openssh-server
systemctl status sshd
```

**Diagnóstico:** `dpkg` no devolvía nada: el paquete no estaba instalado, porque no se marcó "Install OpenSSH server" en el instalador.

**Solución:**
```bash
sudo apt update
sudo apt install -y openssh-server
ss -tulpn | grep :22
```

**Prevención:** revisar las opciones marcadas del instalador. Comprobar que un servicio está instalado y activo antes de intentar conectarse.

---

## 2. SSH aparece "enabled" pero "inactive"

**Síntoma:** `systemctl status ssh` muestra `enabled` e `inactive (dead)`.

**Hipótesis:** (1) activación por socket (`ssh.socket`); (2) servicio parado; (3) configuración errónea.

**Comprobaciones:**
```bash
ss -tulpn | grep :22
systemctl status ssh.socket
sudo journalctl -u ssh -n 20 --no-pager
sudo sshd -t
```

**Diagnóstico:** el estado del servicio no equivale a que SSH funcione. Lo que cuenta es que algo escuche en el puerto 22 y que una conexión real funcione.

**Solución:** `sudo systemctl start ssh` y probar una conexión desde otro equipo.

**Prevención:** verificar con una prueba funcional, no solo con `status`. Ante un fallo de servicio, mirar `journalctl`.

---

# Docker y PostgreSQL

## 3. `Connection refused` al conectar con PostgreSQL

**Síntoma:** `/health` responde 200, pero `/health/db` y los endpoints con datos devuelven 500. El log muestra `connection to server at "localhost", port 5432 failed: Connection refused`.

**Hipótesis:** (1) contenedor de PostgreSQL parado; (2) puerto o credenciales incorrectos.

**Comprobaciones:**
```bash
docker compose ps
ss -tulpn | grep 5432
docker logs helpdesk-db --tail 5
```

**Diagnóstico:** `Connection refused` significa que nada escucha en el puerto. Un fallo de contraseña daría `password authentication failed`. Tras apagar la VM, los contenedores no arrancaban solos.

**Solución:** `docker compose up -d`.

**Prevención:** añadir `restart: unless-stopped` al servicio `db` del `docker-compose.yml`.

---

## 4. El seed falla con errores de clave foránea

**Síntoma:**
```
ERROR: insert or update on table "computers" violates foreign key constraint
DETAIL: Key (assigned_to)=(1) is not present in table "users".
```
Los primeros `INSERT` sí funcionaban.

**Hipótesis:** los `id` de `users` no empiezan en 1. Los `SERIAL` no se reinician al borrar filas, y un `INSERT` fallido también consume un número de la secuencia.

**Comprobaciones:**
```sql
SELECT id, full_name FROM users;
```

**Diagnóstico:** el seed asumía ids fijos (1, 2, 3...) y la secuencia estaba desplazada por pruebas anteriores, entre ellas un `INSERT` rechazado por un `CHECK`.

**Solución:**
```sql
TRUNCATE departments, categories, priorities, users, technicians,
         computers, tickets, ticket_comments, ticket_history
RESTART IDENTITY CASCADE;
```
y volver a cargar `02_seed.sql`.

**Prevención:** empezar el seed con el `TRUNCATE ... RESTART IDENTITY CASCADE` para que sea repetible. No depender de ids fijos en aplicaciones reales.

---

## 5. La contraseña de `.env` no coincide con la de la base de datos

**Síntoma:** `password authentication failed` al conectar.

**Hipótesis:** `DB_PASSWORD` y la contraseña de `DATABASE_URL` son distintas, o la base de datos se creó con otra contraseña.

**Comprobaciones:** comparar ambas variables en `.env`. Probar `docker exec -it helpdesk-db psql -U helpdesk_user -d helpdesk`.

**Diagnóstico:** PostgreSQL fija la contraseña **la primera vez** que crea el volumen. Cambiar `.env` después no la modifica.

**Solución:** usar la misma contraseña en ambas variables. Si cambió después de crear el volumen, hay que recrear el volumen (`docker compose down -v`, **borra los datos**) o cambiarla con `ALTER USER`.

**Prevención:** definir la contraseña una vez y no tocarla. Evitar `@`, `:` y `/` en contraseñas usadas en una URL.

---

# Python y entorno

## 6. `pip install` falla con `pg_config executable not found`

**Síntoma:** al instalar `psycopg2-binary==2.9.9`, pip descarga un `.tar.gz` y falla con `Error: pg_config executable not found`.

**Hipótesis:** no hay paquete precompilado (`.whl`) para la versión de Python en uso, así que pip intenta compilar.

**Comprobaciones:**
```bash
python3 --version
```
La ruta del error contenía `python3.13`.

**Diagnóstico:** la versión fijada era anterior a la compatibilidad con Python 3.13.

**Solución:** subir a `psycopg2-binary==2.9.10` en `requirements.txt` y reinstalar.

**Prevención:** comprobar la versión de Python antes de fijar dependencias. Un `.tar.gz` en una librería "binary" indica que no hay wheel. En Docker se fija la versión de Python en el `Dockerfile`.

---

## 7. `uvicorn: command not found` o `.venv/bin/activate: No such file`

**Síntoma:** `Command 'uvicorn' not found` o `-bash: .venv/bin/activate: No such file or directory`.

**Hipótesis:** (1) el entorno virtual no está activo; (2) se ejecuta desde otra carpeta.

**Comprobaciones:** `pwd`, y mirar si el prompt muestra `(.venv)`.

**Diagnóstico:** uvicorn solo está instalado dentro del `.venv`, que vive en `backend/`.

**Solución:**
```bash
cd ~/helpdesk/backend
source .venv/bin/activate
```

**Prevención:** abrir cada terminal de trabajo con `cd ~/helpdesk/backend && source .venv/bin/activate`. El prompt debe mostrar `(.venv)`.

---

## 8. `Could not import module "app.main"`

**Síntoma:** Uvicorn arranca pero termina con `Error loading ASGI app. Could not import module "app.main"`.

**Hipótesis:** (1) falta código en la rama actual; (2) falta algún `__init__.py`; (3) error de sintaxis o import.

**Comprobaciones:**
```bash
python -c "import app.main"
ls -R app
git branch
```
Importar a mano muestra el error real, que Uvicorn oculta.

**Diagnóstico:** `app/` solo contenía `__pycache__`. El código estaba en una rama que nunca se mergeó a `main`, y al cambiar de rama los archivos desaparecieron del disco.

**Solución:** hacer el merge pendiente (mejor con Pull Request), volver a `main` y comprobar con `ls backend/app`.

**Prevención:** antes de crear una rama nueva, `git branch --merged main` debe incluir la anterior. En GitHub el PR debe poner **Merged**, no solo estar abierto. Probar `python -c "import app.main"` antes de arrancar.

---

## 9. `ImportError: cannot import name 'X' from 'app.schemas'` (o `models`)

**Síntoma:** `cannot import name 'categories' from 'app.routers'`, `cannot import name 'TicketAssign' from 'app.schemas'`.

**Hipótesis:** (1) el archivo o la clase no existe en la rama actual; (2) la edición con `nano` no se guardó; (3) el pegado se cortó o reemplazó contenido.

**Comprobaciones:**
```bash
ls app/routers
grep -n "^class " app/schemas.py
grep -n "^class " app/models.py
git branch
```

**Diagnóstico:** en distintas ocasiones faltaban `categories.py` (rama sin mergear), `TicketAssign`/`TicketStatusChange` (cambio no guardado) y `TicketComment`, `CommentCreate` y `CommentOut` (pegado incompleto).

**Solución:** añadir lo que falte, o vaciar el archivo y pegar la versión completa.

**Prevención:** tras guardar con `nano`, comprobar con `grep` que lo añadido existe. Ejecutar `python -c "import app.main"` antes de cada commit. Contar clases: `models.py` debe tener 10 y `schemas.py` 26.

---

# API y errores HTTP

## 10. `404 Not Found` en un endpoint nuevo

**Síntoma:** `/categories` y `/priorities` devuelven 404, pero `/docs` carga.

**Hipótesis:** el router no está registrado en la aplicación.

**Comprobaciones:**
```bash
cat app/main.py
ls app/routers
```

**Diagnóstico:** `main.py` tenía **dos** líneas `app = FastAPI(...)`. La segunda reemplazaba a la primera junto con los routers registrados antes.

**Solución:** dejar un único bloque en `main.py`.

**Prevención:** `grep -c "app = FastAPI" app/main.py` debe devolver `1`. Cuando se indique "reemplazar el contenido", vaciar el archivo y pegar todo. Un 404 en un endpoint nuevo suele ser un router sin registrar; un 500 apunta a la base de datos o al código.

---

## 11. `404` y `Invalid HTTP request` al abrir la API en el navegador

**Síntoma:** el log muestra `GET / HTTP/1.1 404` y `WARNING: Invalid HTTP request received`.

**Hipótesis:** (1) la URL no incluía la ruta; (2) se usó `https://` en vez de `http://`.

**Diagnóstico:** el navegador pedía `/`, que no existe. El warning proviene de peticiones HTTPS contra un servidor HTTP plano. La API funcionaba bien.

**Solución:** usar `http://IP_DE_LA_VM:8000/docs`.

**Prevención:** guardar la URL en favoritos. Un 404 significa "esa ruta no existe", no que algo esté roto. Opcional: redirigir `/` a `/docs`.

---

## 12. `500` por `ResponseValidationError` en el email

**Síntoma:** el login y el token funcionan, pero `GET /auth/me` devuelve 500.
```
ResponseValidationError ... 'loc': ('response', 'email') ...
The part after the @-sign is a special-use or reserved name
```

**Hipótesis:** fallo al leer el token o al serializar la respuesta.

**Comprobaciones:** leer la **última línea del traceback** en la terminal de Uvicorn.

**Diagnóstico:** `.test` es un dominio reservado y `EmailStr` lo rechaza. Al devolver el usuario, FastAPI volvía a validar el email con `EmailStr` y fallaba.

**Solución:** `UserOut.email` pasa a `str`. La validación estricta se mantiene en `UserCreate` y `UserUpdate`.

**Prevención:** ante un 500, leer el traceback antes de tocar nada. `ResponseValidationError` significa que el código funcionó pero la respuesta no cumple el esquema (distinto de un 422, donde falla la petición). Para datos de prueba nuevos, usar `@example.com`.

---

## 13. Códigos HTTP: cuándo usar cada uno

Referencia de las decisiones tomadas en la API:

| Código | Significado | Ejemplo en el proyecto |
|---|---|---|
| 200 / 201 / 204 | Correcto / creado / borrado sin cuerpo | Crear departamento, borrar equipo |
| 401 | No autenticado | Token ausente, caducado o manipulado |
| 403 | Autenticado sin permiso | Rol insuficiente |
| 404 | No existe | Ticket inexistente |
| 409 | El estado actual lo impide | Nombre duplicado, transición ilegal, borrar con dependencias |
| 422 | Datos de la petición inválidos | Email mal formado, prioridad inexistente |
| 500 | Error no controlado del servidor | Ver caso 12 |

**Prevención:** un 4xx indica un problema de la petición; un 5xx, del servidor. Los 5xx se diagnostican en el log.

---

## 14. Respuestas vacías al consultar con `curl` (variable `$ID` vacía)

**Síntoma:** `curl -s http://localhost:8000/tickets/$ID/history | ... | grep field_name` no imprime nada.

**Hipótesis:** la variable `$ID` está vacía y la URL queda como `/tickets//history`.

**Comprobaciones:**
```bash
echo "ID=[$ID]"
curl -s -w "\nHTTP %{http_code}\n" http://localhost:8000/tickets/$ID/history
```

**Diagnóstico:** las variables de shell mueren con la terminal. Se había abierto otra sesión.

**Solución:** volver a crear el ticket y guardar su id en la misma terminal.

**Prevención:** `echo $ID` antes de usarla. Un `grep` sin salida no significa "no hay datos"; puede que la petición ni llegara. Usar `-w "\nHTTP %{http_code}\n"`.

---

# Git y GitHub

## 15. `src refspec ... does not match any`

**Síntoma:**
```
error: src refspec feature/crud-computers does not match any
error: failed to push some refs
```

**Hipótesis:** la rama que se intenta subir no existe en local.

**Comprobaciones:** `git branch` y el nombre entre corchetes del último commit: `[rama hash]`.

**Diagnóstico:** el commit se hizo en `feature/crud-users-technicians` porque no se creó la rama nueva. El `push` apuntaba a una rama inexistente.

**Solución:** subir la rama donde está el commit (`git push -u origin feature/crud-users-technicians`) y hacer un único PR.

**Prevención:** tras `git checkout -b`, ejecutar `git branch`: el asterisco indica la rama actual. Leer el nombre entre corchetes al hacer commit.

---

## 16. Conflicto de merge

**Síntoma:**
```
CONFLICT (content): Merge conflict in backend/app/main.py
Automatic merge failed; fix conflicts and then commit the result.
```

**Hipótesis:** dos ramas modificaron las mismas líneas.

**Comprobaciones:**
```bash
git status
grep -rn -E "^(<<<<<<<|=======|>>>>>>>)" backend/app --include=*.py
```

**Diagnóstico:** la rama de usuarios y la de categorías añadieron contenido al final de `models.py` y `schemas.py`, y Git no puede decidir cuál conservar.

**Solución:** editar los archivos conservando ambas partes, borrar las marcas `<<<<<<<`, `=======` y `>>>>>>>`, comprobar el import, `git add` y `git commit`. Salida de emergencia: `git merge --abort`.

**Prevención:** mergear cada rama a `main` antes de empezar la siguiente. Los conflictos aparecen por ramas acumuladas sin integrar.

---

## 17. `remote: Internal Server Error` al subir un tag

**Síntoma:** `git push origin v0.1.0` falla con `remote: Internal Server Error` y un `Request ID`. Antes, `fatal: tag 'v0.1.0' already exists`.

**Hipótesis:** error local (clave, configuración) o incidencia del proveedor.

**Comprobaciones:**
```bash
curl -s https://www.githubstatus.com/api/v2/status.json | python3 -m json.tool | grep description
curl -s https://www.githubstatus.com/api/v2/components.json | python3 ~/ghstatus.py
git ls-remote --tags origin
```

**Diagnóstico:** el prefijo `remote:` indica fallo del servidor. La API de estado mostró `Partial System Outage`, con Pull Requests y Webhooks en `major_outage` y Git Operations degradado. El aviso `already exists` era el tag local, que se había creado bien.

**Solución:** no tocar la configuración. Trabajar con commits locales, esperar a que el servicio se recupere y reintentar. Alternativa: `gh release create`.

**Prevención:** consultar la página de estado del proveedor antes de modificar nada. Saber distinguir un fallo propio de uno externo evita perder tiempo.

---

## 18. No aparece "Compare & pull request" en GitHub

**Síntoma:** no se ve el banner para crear el PR.

**Hipótesis:** (1) el push no llegó; (2) el banner caduca; (3) Pull Requests estaba caído.

**Comprobaciones:**
```bash
git ls-remote --heads origin
git log --oneline -3
```

**Diagnóstico:** la rama sí estaba en GitHub y el PR ya se había mergeado tras recuperarse el servicio. `git pull` en `main` trajo los cambios con `Fast-forward`.

**Solución:** crear el PR a mano en `.../compare/main...rama` si hace falta, o comprobar en **Pull requests → Closed** que ya está **Merged**.

**Prevención:** verificar el estado real con `git log` y `git ls-remote` en vez de depender de un banner.

---

## 19. Deshacer cambios sin perder trabajo

**Síntoma:** necesidad de volver a un estado anterior tras un error (por ejemplo, un tag local que no se podía subir).

**Comprobaciones:** `git status`, `git branch`, `git log --oneline -8`, `git tag -l`.

**Soluciones según el caso:**
```bash
git tag -d v0.1.0          # solo quitar un tag local
git restore archivo        # descartar cambios sin commit
git branch backup-antes    # copia de seguridad antes de algo destructivo
```

**Prevención:** `git reset --hard` y `git clean -f` destruyen trabajo. Crear una rama de respaldo antes. En ramas ya subidas, usar `git revert` en lugar de reescribir el historial.

---

# Edición de archivos

## 20. Contenido añadido que no queda guardado o queda duplicado

**Síntoma:** faltan clases tras pegar, o aparecen bloques repetidos.

**Hipótesis:** (1) `nano` se cerró sin guardar; (2) el pegado se cortó; (3) se pegó encima en vez de al final.

**Comprobaciones:**
```bash
tail -5 archivo
grep -c "patrón" archivo
python -c "import app.main"
```

**Diagnóstico:** ocurrió con `schemas.py`, `models.py`, `tickets.py` y `main.py`.

**Solución:** vaciar el archivo (`> archivo`) y pegar la versión completa.

**Prevención:** comprobar siempre con `grep` o `tail` que el contenido está. `git diff` antes de `git add` muestra qué se va a subir.

---

## 21. Errores de recuento de comprobación

**Síntoma:** `grep -c "^class "` devuelve valores distintos a los esperados (10 en `models.py`, 26 en `schemas.py`).

**Diagnóstico:** el recuento correcto incluye `Base` en `models.py`. El valor esperado inicial era erróneo, no el archivo.

**Prevención:** validar el valor esperado contra la estructura real antes de concluir que algo falla.

---

# Terminal y shell

## 22. `IndentationError: unexpected indent` al pegar un `python -c`

**Síntoma:**
```
File "<string>", line 2
    import sys, json
IndentationError: unexpected indent
```

**Hipótesis:** espacios sobrantes al copiar un comando multilínea.

**Diagnóstico:** Python es sensible a la sangría y la primera línea no puede ir indentada.

**Solución:** guardar el script en un archivo (`~/ghstatus.py`) y ejecutarlo con `python3 ~/ghstatus.py`.

**Prevención:** para scripts de más de una línea, usar un archivo en vez de `python -c`.

---

## 23. Comandos de Git y Python ejecutados en el lugar equivocado

**Síntoma:** comandos que funcionan en una terminal y no en otra.

**Diagnóstico:** los comandos de Git no necesitan el `.venv`, pero sí estar dentro del repositorio. Los de Python (`uvicorn`, `pip`, `pytest`) sí necesitan el entorno activo. Una terminal ocupada por Uvicorn no puede usarse para otros comandos.

**Prevención:** usar una terminal para la API y otra para pruebas y Git. Antes de ejecutar, comprobar con `pwd` y el prompt.

## 24. Pull Request abierto con conflictos que ya no hacen falta

**Síntoma:** un PR antiguo (`feature/tickets-comments` → `main`) muestra `This branch has conflicts that must be resolved` en `models.py`, `schemas.py` y `tickets.py`.

**Hipótesis:** (1) `main` ya contiene ese código por otra rama; (2) `main` no lo tiene y hay que integrarlo.

**Comprobaciones:**
```bash
git fetch origin
git branch --merged main
git log --oneline --all --graph | head -15
grep -c "^class " backend/app/models.py backend/app/schemas.py
grep -c "def comment_to_out" backend/app/routers/tickets.py
```

**Diagnóstico:** los tres archivos en conflicto se habían reescrito por completo en una rama posterior (`feature/tickets-history`), ya mergeada. El PR antiguo quedó abierto y desfasado, y por eso chocaba con `main`.

**Solución:** comprobar que `main` ya tiene el contenido (10 clases en `models.py`, 26 en `schemas.py`), cerrar el PR sin mergear y borrar la rama (`git push origin --delete rama`, `git branch -D rama`).

**Prevención:** mergear cada PR antes de crear la rama siguiente. Si una rama posterior reescribe los mismos archivos, cerrar el PR anterior en vez de resolver conflictos de código que ya está integrado. Revisar de vez en cuando la pestaña **Pull requests** por si queda alguno abierto.

# Seguridad y acceso

## 25. Un usuario no puede iniciar sesión: `429 Too Many Requests`

**Síntoma:** el login devuelve `429` con "Demasiados intentos fallidos", incluso con la contraseña correcta.

**Hipótesis:** (1) el usuario falló 5 veces desde esa IP y está bloqueado temporalmente; (2) un atacante está probando contraseñas; (3) un cliente automático reintenta con credenciales viejas.

**Comprobaciones:**
```bash
grep "Login bloqueado" backend/logs/helpdesk.log | tail
grep "Login fallido" backend/logs/helpdesk.log | tail
```
La cabecera `Retry-After` indica los segundos que faltan.

**Diagnóstico:** el bloqueo es por IP + email y dura 15 minutos. Si hay muchos fallos para emails distintos desde una misma IP, es un intento de fuerza bruta; si es un solo usuario, suele ser una contraseña olvidada o guardada con un valor antiguo.

**Solución:** esperar a que acabe el bloqueo (o reiniciar la API, que borra el contador en memoria, solo en laboratorio). Si es un olvido, un administrador restablece la contraseña con `PATCH /users/{id}`.

**Prevención:** informar al usuario del límite. En producción, persistir el contador (Redis) y alertar si hay muchos bloqueos desde una IP.

# Rendimiento de base de datos

## 26. Las búsquedas de tickets son lentas

**Síntoma:** `GET /tickets?q=texto` tarda cada vez más a medida que crece la tabla.

**Hipótesis:** (1) falta un índice adecuado; (2) el índice existe pero no sirve para esa consulta; (3) las estadísticas del planificador están desactualizadas.

**Comprobaciones:**
```sql
EXPLAIN (ANALYZE, BUFFERS) SELECT id FROM tickets WHERE title ILIKE '%texto%';
\di+ idx_tickets_*
SELECT indexrelname, idx_scan FROM pg_stat_user_indexes WHERE relname = 'tickets';
```

**Diagnóstico:** el plan mostraba `Seq Scan` con muchas filas descartadas. Un índice B-tree normal no acelera `ILIKE '%texto%'`, porque el patrón empieza por comodín.

**Solución:** extensión `pg_trgm` e índices GIN con `gin_trgm_ops` sobre título y descripción (`database/04_indexes.sql`); índice compuesto `(assigned_to, status, created_at DESC)` para la bandeja del técnico. Después, `ANALYZE tickets`.

**Prevención:** medir con `EXPLAIN ANALYZE` antes de crear índices y no indexar a ciegas: cada índice ralentiza las escrituras y ocupa espacio. Con términos muy frecuentes, `Seq Scan` puede ser la mejor opción. Revisar `idx_scan` para detectar índices sin uso.

## 27. `tail: cannot open 'logs/helpdesk.log'`

**Síntoma:** `tail: cannot open 'logs/helpdesk.log' for reading: No such file or directory`.

**Hipótesis:** (1) el archivo no existe; (2) se ejecuta desde otra carpeta; (3) el log se creó en otra ruta.

**Comprobaciones:**
```bash
pwd
ls ~/helpdesk/backend/logs
```

**Diagnóstico:** el comando se ejecutó desde `frontend/` y la ruta `logs/` es relativa. El log vive en `backend/logs/`.

**Solución:** usar la ruta absoluta: `tail -5 ~/helpdesk/backend/logs/helpdesk.log`.

**Prevención:** comprobar con `pwd` dónde se está antes de usar rutas relativas. Preferir rutas absolutas en comandos de diagnóstico.

## 28. El límite de login agrupa a todos los usuarios tras Nginx (IP `127.0.0.1` o `None`)

**Síntoma:** al poner Nginx delante de la API, el log muestra `ip=127.0.0.1` para todos los logins, y cinco fallos de un usuario podrían bloquear a otros. Más tarde aparece `ip=None` en logins hechos desde la propia máquina.

**Hipótesis:** (1) FastAPI ve la IP de Nginx y no la del cliente; (2) Nginx no reenvía la IP; (3) Uvicorn no confía en la cabecera.

**Comprobaciones:**
```bash
tail -5 ~/helpdesk/backend/logs/helpdesk.log
ps aux | grep "[u]vicorn"
grep X-Forwarded-For /etc/nginx/sites-available/helpdesk
```
Prueba con una IP simulada:
```bash
for i in 1 2 3 4 5; do curl -s -o /dev/null -w "%{http_code} " -X POST http://localhost:8080/api/auth/login -H "X-Forwarded-For: 203.0.113.9" -d 'username=carlos@empresa.test&password=mala'; done; echo
```

**Diagnóstico:** tras un proxy inverso, la conexión TCP llega siempre desde Nginx (`127.0.0.1`). La IP real viaja en `X-Forwarded-For`. Uvicorn solo la usa si se arranca con `--proxy-headers` y la IP del proxy figura en `--forwarded-allow-ips`. Si el origen es la propia máquina, la IP de Nginx se descarta como de confianza y `request.client.host` puede quedar en `None`.

**Solución:**
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips 127.0.0.1 --reload
```
y en `auth.py`: `ip = (request.client.host if request.client else None) or "desconocida"`. Resultado: `401` ×5 y `429` al sexto desde la misma IP, y otro usuario sigue entrando (`200`).

**Prevención:** confiar en `X-Forwarded-For` solo desde el proxy (nunca `*`), porque si no un atacante falsearía su IP y evitaría el bloqueo. Con `--host 127.0.0.1` la API solo es accesible a través de Nginx.

## 29. Un script SQL del repositorio no existe (`No such file or directory`)

**Síntoma:** al cargar `database/01_schema.sql` en la base de test: `No such file or directory`, seguido de `relation "tickets" does not exist` al cargar los índices.

**Hipótesis:** (1) el archivo está en una rama no integrada; (2) tiene otro nombre; (3) se borró.

**Comprobaciones:**
```bash
ls database
git ls-tree -r --name-only main | grep database
git log --oneline --all -- database/01_schema.sql | head
```

**Diagnóstico:** el esquema nunca llegó a `main` y la rama que lo contenía se borró en la limpieza. El commit seguía en el historial.

**Solución:** `git checkout <commit> -- database/01_schema.sql`, commitearlo en una rama y mergearlo. Después recrear la base de test (`DROP DATABASE` / `CREATE DATABASE`) y cargar el esquema antes que los índices.

**Prevención:** antes de borrar una rama, `git branch --merged main` debe incluirla. Los scripts SQL se cargan en orden (`01_`, `02_`...). Un `git log --all -- archivo` encuentra archivos de ramas ya borradas.
