"""Asigna las contraseñas de desarrollo a los usuarios del seed (solo laboratorio).

Cada usuario: su nombre sin espacios + "Help2026" (p. ej. TecnicoAHelp2026).
"""
from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.security import hash_password

PASSWORD_SUFFIX = "Help2026"


def main() -> None:
    with SessionLocal() as db:
        users = db.scalars(select(User).where(User.email.like("%@empresa.test"))).all()
        for user in users:
            user.password_hash = hash_password(user.full_name.replace(" ", "") + PASSWORD_SUFFIX)
        db.commit()
        print(f"Contraseñas de desarrollo asignadas a {len(users)} usuarios")


if __name__ == "__main__":
    main()
