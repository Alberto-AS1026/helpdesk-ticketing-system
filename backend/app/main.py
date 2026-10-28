from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import CORS_ORIGINS
from app.database import get_db
from app.dependencies import ADMIN_ONLY, ALL_ROLES, STAFF, protect
from app.logging_config import setup_logging
from app.routers import (
    auth,
    categories,
    chat,
    computers,
    departments,
    priorities,
    stats,
    technicians,
    tickets,
    users,
)

setup_logging()

app = FastAPI(title="Help Desk API", version="0.11.0")

# CORS: solo los orígenes de la lista blanca
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    """Añade cabeceras de seguridad a todas las respuestas."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


# Público: login
app.include_router(auth.router)

# Política de permisos: un único lugar para auditar quién puede qué
app.include_router(
    departments.router, dependencies=[Depends(protect(read=ALL_ROLES, write=ADMIN_ONLY))]
)
app.include_router(
    categories.router, dependencies=[Depends(protect(read=ALL_ROLES, write=ADMIN_ONLY))]
)
app.include_router(
    priorities.router, dependencies=[Depends(protect(read=ALL_ROLES, write=ADMIN_ONLY))]
)
app.include_router(
    users.router, dependencies=[Depends(protect(read=STAFF, write=ADMIN_ONLY))]
)
app.include_router(
    technicians.router, dependencies=[Depends(protect(read=STAFF, write=ADMIN_ONLY))]
)
app.include_router(
    computers.router, dependencies=[Depends(protect(read=ALL_ROLES, write=STAFF))]
)
app.include_router(
    stats.router, dependencies=[Depends(protect(read=STAFF, write=ADMIN_ONLY))]
)
app.include_router(
    tickets.router, dependencies=[Depends(protect(read=ALL_ROLES, write=ALL_ROLES))]
)
app.include_router(
    chat.router, dependencies=[Depends(protect(read=ALL_ROLES, write=ALL_ROLES))]
)
# WebSocket del chat: se autentica con el primer mensaje (ver routers/chat.py)
app.include_router(chat.ws_router)


@app.get("/health")
def health():
    """La API está viva."""
    return {"status": "ok"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    """La API puede hablar con la base de datos."""
    db.execute(text("SELECT 1"))
    return {"database": "ok"}
