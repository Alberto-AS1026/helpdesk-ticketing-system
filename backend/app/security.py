from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY


def hash_password(password: str) -> str:
    """Devuelve el hash bcrypt (con salt incluido) de una contraseña."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Comprueba si la contraseña coincide con el hash guardado."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # Hash con formato inválido (por ejemplo, el 'hash_de_prueba' del seed)
        return False


def create_access_token(user_id: int) -> str:
    """Crea un JWT firmado que caduca pasado el tiempo configurado."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Verifica firma y caducidad. Lanza jwt.PyJWTError si el token no es válido."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
