import bcrypt


def hash_password(password: str) -> str:
    """Devuelve el hash bcrypt (con salt incluido) de una contraseña."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Comprueba si la contraseña coincide con el hash guardado."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
