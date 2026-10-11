import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.ratelimit import login_limiter
from app.schemas import TokenOut, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])
security_log = logging.getLogger("helpdesk.security")

# Se usa cuando el email no existe, para que el login tarde lo mismo
# en ambos casos y no revele qué emails están registrados.
DUMMY_HASH = hash_password("contraseña-ficticia")


@router.post("/login", response_model=TokenOut)
def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """El campo 'username' del formulario es el email."""
    ip = request.client.host if request.client else "desconocida"
    key = f"{ip}|{form.username.lower()}"

    wait = login_limiter.retry_after(key)
    if wait:
        security_log.warning("Login bloqueado ip=%s usuario=%r espera=%ss", ip, form.username, wait)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos fallidos. Inténtalo más tarde",
            headers={"Retry-After": str(wait)},
        )

    user = db.scalars(select(User).where(User.email == form.username)).first()
    password_ok = verify_password(form.password, user.password_hash if user else DUMMY_HASH)

    if user is None or not password_ok or not user.is_active:
        login_limiter.register_failure(key)
        security_log.warning("Login fallido ip=%s usuario=%r", ip, form.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    login_limiter.reset(key)
    security_log.info("Login correcto ip=%s usuario_id=%s rol=%s", ip, user.id, user.role)
    return TokenOut(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    """Datos del usuario autenticado."""
    return current_user
