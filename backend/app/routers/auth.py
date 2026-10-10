from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import TokenOut, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])

# Se usa cuando el email no existe, para que el login tarde lo mismo
# en ambos casos y no revele qué emails están registrados.
DUMMY_HASH = hash_password("contraseña-ficticia")


@router.post("/login", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """El campo 'username' del formulario es el email."""
    user = db.scalars(select(User).where(User.email == form.username)).first()
    password_ok = verify_password(form.password, user.password_hash if user else DUMMY_HASH)

    if user is None or not password_ok or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenOut(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    """Datos del usuario autenticado."""
    return current_user
