import threading
import time
from collections import deque

from app.config import LOGIN_MAX_ATTEMPTS, LOGIN_WINDOW_SECONDS


class LoginRateLimiter:
    """Cuenta fallos de login por clave (IP + email) en una ventana de tiempo."""

    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._failures: dict[str, deque] = {}
        self._lock = threading.Lock()

    def retry_after(self, key: str) -> int:
        """Segundos que faltan para poder reintentar; 0 si no está bloqueado."""
        now = time.monotonic()
        with self._lock:
            attempts = self._failures.get(key)
            if not attempts:
                return 0
            while attempts and now - attempts[0] > self.window:
                attempts.popleft()
            if not attempts:
                del self._failures[key]
                return 0
            if len(attempts) >= self.max_attempts:
                return int(self.window - (now - attempts[0])) + 1
            return 0

    def register_failure(self, key: str) -> None:
        with self._lock:
            self._failures.setdefault(key, deque()).append(time.monotonic())

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)


login_limiter = LoginRateLimiter(LOGIN_MAX_ATTEMPTS, LOGIN_WINDOW_SECONDS)
