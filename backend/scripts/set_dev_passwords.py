"""Asigna una contraseña de desarrollo a los usuarios del seed (solo laboratorio)."""
from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.security import hash_password

DEV_PASSWORD = "Helpdesk_2026"


def main() -> None:
    with SessionLocal() as db:
        users = db.scalars(select(User).where(User.email.like("%@empresa.test"))).all()
        for user in users:
            user.password_hash = hash_password(DEV_PASSWORD)
        db.commit()
        print(f"Contraseña de desarrollo asignada a {len(users)} usuarios")


if __name__ == "__main__":
    main()
