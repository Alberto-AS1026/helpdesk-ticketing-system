"""Conexiones WebSocket abiertas y envío de avisos en tiempo real.

Los endpoints REST (síncronos, en el pool de hilos) llaman a notify(); el
envío se programa en el bucle de eventos donde viven los sockets.

Limitación: el registro está en memoria, así que solo funciona con un único
proceso de uvicorn (como en el Dockerfile). Con varios procesos o réplicas
habría que repartir los avisos con PostgreSQL LISTEN/NOTIFY.
"""
import asyncio
import logging
import threading
from datetime import datetime

from fastapi import WebSocket

log = logging.getLogger("helpdesk.realtime")

# Pestañas abiertas a la vez por usuario
MAX_CONNECTIONS_PER_USER = 10


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = {}
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        # Cuándo cerró su última conexión cada usuario (ver went_offline_after)
        self._offline_at: dict[int, datetime] = {}

    def connect(self, user_id: int, ws: WebSocket) -> bool:
        """Registra el socket. Devuelve False si el usuario ya tiene demasiados."""
        self._loop = asyncio.get_running_loop()
        with self._lock:
            sockets = self._connections.setdefault(user_id, set())
            if len(sockets) >= MAX_CONNECTIONS_PER_USER:
                return False
            sockets.add(ws)
            self._offline_at.pop(user_id, None)
            return True

    def disconnect(self, user_id: int, ws: WebSocket) -> bool:
        """Quita el socket. Devuelve True si era la última conexión del usuario."""
        with self._lock:
            sockets = self._connections.get(user_id)
            if not sockets:
                return False
            sockets.discard(ws)
            if sockets:
                return False
            del self._connections[user_id]
            return True

    def is_online(self, user_id: int) -> bool:
        with self._lock:
            return bool(self._connections.get(user_id))

    def mark_offline(self, user_id: int, last_seen: datetime) -> None:
        with self._lock:
            if not self._connections.get(user_id):
                self._offline_at[user_id] = last_seen

    def went_offline_after(self, user_id: int, last_seen: datetime) -> bool:
        """True si cerró el WebSocket y no ha habido actividad desde entonces:
        así no se le muestra "en línea" durante la ventana del plan B."""
        with self._lock:
            offline = self._offline_at.get(user_id)
        return offline is not None and last_seen <= offline

    def notify(self, user_ids, event: dict) -> None:
        """Envía un aviso a todas las pestañas de esos usuarios. Se puede llamar desde cualquier hilo."""
        with self._lock:
            targets = [ws for uid in set(user_ids) for ws in self._connections.get(uid, ())]
        if not targets or self._loop is None or self._loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(self._send(targets, event), self._loop)

    @staticmethod
    async def _send(targets: list[WebSocket], event: dict) -> None:
        for ws in targets:
            try:
                await ws.send_json(event)
            except Exception:  # socket cerrándose: su bucle lo dará de baja
                log.debug("No se pudo enviar el aviso a un socket")


manager = ConnectionManager()

# Referencias a las tareas lanzadas con spawn() para que no las recoja el GC
_background: set[asyncio.Task] = set()


def spawn(coro) -> None:
    """Lanza una tarea independiente de la conexión actual: si el socket se
    cancela al cerrarse, la tarea (por ejemplo, avisar de la desconexión) sigue."""
    task = asyncio.get_running_loop().create_task(coro)
    _background.add(task)
    task.add_done_callback(_background.discard)
