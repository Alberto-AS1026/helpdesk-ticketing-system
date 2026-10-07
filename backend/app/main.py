from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers import departments

app = FastAPI(title="Help Desk API", version="0.2.0")

app.include_router(departments.router)


@app.get("/health")
def health():
    """La API está viva."""
    return {"status": "ok"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    """La API puede hablar con la base de datos."""
    db.execute(text("SELECT 1"))
    return {"database": "ok"}
