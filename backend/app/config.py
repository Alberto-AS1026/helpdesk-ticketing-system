import os
from pathlib import Path

from dotenv import load_dotenv

# Carga el .env de la raíz del proyecto
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise RuntimeError("Falta SECRET_KEY en el .env (mínimo 32 caracteres)")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# Orígenes que pueden llamar a la API desde un navegador (lista blanca)
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:8080").split(",")
    if origin.strip()
]

# Límite de intentos de login fallidos
LOGIN_MAX_ATTEMPTS = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_WINDOW_SECONDS = int(os.getenv("LOGIN_WINDOW_SECONDS", "900"))
