import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
if not TEST_DATABASE_URL or not TEST_DATABASE_URL.rsplit("/", 1)[-1].endswith("_test"):
    raise RuntimeError("TEST_DATABASE_URL debe apuntar a una base cuyo nombre termine en '_test'")

# Debe fijarse ANTES de importar la aplicación
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.database import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    Category, Department, Priority, Technician, User,
)
from app.ratelimit import login_limiter  # noqa: E402
from app.security import hash_password  # noqa: E402

PASSWORD = "Test_Password_1"

# Un hash por ejecución (bcrypt es lento a propósito)
PASSWORD_HASH = hash_password(PASSWORD)

TABLES = (
    "ticket_history, ticket_comments, tickets, computers, technicians, "
    "users, priorities, categories, departments"
)


@pytest.fixture(autouse=True)
def clean_db():
    """Antes de cada test: base vacía, datos mínimos conocidos y límite de login a cero."""
    assert engine.url.database.endswith("_test"), "¡Los tests solo pueden tocar una base _test!"
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {TABLES} RESTART IDENTITY CASCADE"))

    with SessionLocal() as db:
        db.add(Department(name="IT"))
        db.add_all([Category(name="Hardware"), Category(name="Software")])
        db.add_all([Priority(name="Baja", level=1), Priority(name="Alta", level=3)])
        db.flush()
        db.add_all([
            User(full_name="Admin Test", email="admin@test.example", password_hash=PASSWORD_HASH, role="admin"),
            User(full_name="Tecnico Uno", email="tech1@test.example", password_hash=PASSWORD_HASH, role="technician"),
            User(full_name="Usuario Uno", email="user1@test.example", password_hash=PASSWORD_HASH, role="user"),
            User(full_name="Usuario Dos", email="user2@test.example", password_hash=PASSWORD_HASH, role="user"),
        ])
        db.flush()
        db.add(Technician(user_id=2, specialty="Sistemas", level="N1"))
        db.commit()

    login_limiter._failures.clear()
    yield


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def _login(client, email):
    r = client.post("/auth/login", data={"username": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


@pytest.fixture
def admin(client):
    return _login(client, "admin@test.example")


@pytest.fixture
def tech(client):
    return _login(client, "tech1@test.example")


@pytest.fixture
def user1(client):
    return _login(client, "user1@test.example")


@pytest.fixture
def user2(client):
    return _login(client, "user2@test.example")



# ---------- Helpers para tests de tickets ----------

def create_ticket(client, headers, **overrides):
    """Crea un ticket y devuelve su JSON (comprueba que da 201)."""
    body = {
        "title": "Pantalla negra",
        "description": "El monitor no enciende",
        "priority_id": 1,
        "category_id": 1,
    }
    body.update(overrides)
    r = client.post("/tickets", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def set_status(client, headers, ticket_id, status, **extra):
    return client.patch(
        f"/tickets/{ticket_id}/status", json={"status": status, **extra}, headers=headers
    )


def assign(client, headers, ticket_id, technician_id=1):
    return client.patch(
        f"/tickets/{ticket_id}/assign", json={"technician_id": technician_id}, headers=headers
    )
