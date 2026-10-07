# Troubleshooting

Guía de diagnóstico de problemas reales encontrados durante el desarrollo.
Cada caso sigue el mismo método: síntoma, hipótesis, comprobaciones,
comandos, diagnóstico, solución y prevención.

---

## 1. SSH aparece "inactive" aunque está habilitado

**Síntoma:** `systemctl status ssh` muestra `enabled` pero `inactive (dead)`.

**Hipótesis:**
1. Ubuntu usa activación por socket (`ssh.socket`) y el servicio solo arranca al recibir una conexión.
2. El servicio está parado o falló al arrancar.
3. Error en la configuración de SSH.

**Comprobaciones y comandos:**
```bash
ss -tulpn | grep :22
systemctl status ssh.socket
sudo journalctl -u ssh -n 20 --no-pager
sudo sshd -t
```

**Diagnóstico:** el estado del servicio no equivale a que SSH funcione. Lo que cuenta es que haya algo escuchando en el puerto 22 y que se pueda conectar.

**Solución:** `sudo systemctl start ssh` y probar una conexión real.

**Prevención:** verificar con una prueba funcional, no solo con `status`; revisar `journalctl` ante cualquier fallo de servicio.

---

## 2. `Connection refused` en `/health/db`

**Síntoma:** la API responde en `/health` (200) pero `/health/db` y los endpoints con base de datos devuelven 500.

**Hipótesis:**
1. El contenedor de PostgreSQL está parado.
2. Puerto o credenciales incorrectos.

**Comprobaciones y comandos:**
```bash
docker compose ps
ss -tulpn | grep 5432
docker logs helpdesk-db --tail 5
```

**Diagnóstico:** `Connection refused` significa que nada escucha en el puerto 5432. Un fallo de contraseña daría `password authentication failed`. Tras apagar la VM, los contenedores no arrancan solos.

**Solución:** `docker compose up -d`.

**Prevención:** añadir `restart: unless-stopped` al servicio `db` del `docker-compose.yml`.

---

## 3. `remote: Internal Server Error` al subir un tag

**Síntoma:** `git push origin v0.1.0` falla con `Internal Server Error` y un `Request ID`.

**Hipótesis:** error local (clave, configuración) o incidencia del proveedor.

**Comprobaciones y comandos:**
```bash
curl -s https://www.githubstatus.com/api/v2/status.json | python3 -m json.tool | grep description
curl -s https://www.githubstatus.com/api/v2/components.json
```

**Diagnóstico:** el prefijo `remote:` indica fallo del servidor. La API de estado mostró `Partial System Outage`, con Pull Requests y Git Operations afectados.

**Solución:** no tocar la configuración local; trabajar con commits locales y subir cuando el servicio se recupere.

**Prevención:** consultar la página de estado del proveedor antes de modificar nada.
