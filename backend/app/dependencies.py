import logging

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
security_log = logging.getLogger("helpdesk.security")

# Grupos de roles reutilizables
ALL_ROLES = ("user", "technician", "admin")
STAFF = ("technician", "admin")
ADMIN_ONLY = ("admin",)

READ_METHODS = {"GET", "HEAD", "OPTIONS"}


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Devuelve el usuario del token, o responde 401."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales no válidas o sesión caducada",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        security_log.warning("Token no válido o caducado")
        raise credentials_error

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        security_log.warning("Token de usuario inexistente o desactivado id=%s", user_id)
        raise credentials_error
    return user


def deny(user: User, action: str) -> None:
    """Registra y responde 403."""
    security_log.warning("Acceso denegado usuario_id=%s rol=%s accion=%s", user.id, user.role, action)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tienes permisos para esta acción",
    )


def require_roles(*roles: str):
    """Exige que el usuario tenga uno de los roles indicados."""

    def checker(request: Request, user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            deny(user, f"{request.method} {request.url.path}")
        return user

    return checker


def protect(read: tuple[str, ...], write: tuple[str, ...]):
    """Política por router: un conjunto de roles para leer y otro para escribir."""

    def checker(request: Request, user: User = Depends(get_current_user)) -> User:
        allowed = read if request.method in READ_METHODS else write
        if user.role not in allowed:
            deny(user, f"{request.method} {request.url.path}")
        return user

    return checker
