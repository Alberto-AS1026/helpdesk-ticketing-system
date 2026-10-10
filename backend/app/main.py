from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import ADMIN_ONLY, ALL_ROLES, STAFF, protect
from app.routers import (
    auth,
    categories,
    computers,
    departments,
    priorities,
    technicians,
    tickets,
    users,
)

app = FastAPI(title="Help Desk API", version="0.9.0")

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
    tickets.router, dependencies=[Depends(protect(read=ALL_ROLES, write=ALL_ROLES))]
)


@app.get("/health")
def health():
    """La API está viva."""
    return {"status": "ok"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    """La API puede hablar con la base de datos."""
    db.execute(text("SELECT 1"))
    return {"database": "ok"}
