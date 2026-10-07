from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

app = FastAPI(title="Help Desk API", version="0.1.0")


@app.get("/health")
def health():
    """La API está viva."""
    return {"status": "ok"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    """La API puede hablar con la base de datos."""
    db.execute(text("SELECT 1"))
    return {"database": "ok"}


@app.get("/departments")
def list_departments(db: Session = Depends(get_db)):
    """Lista departamentos con SQL directo (temporal)."""
    rows = db.execute(text("SELECT id, name, description FROM departments ORDER BY id"))
    return [dict(r._mapping) for r in rows]
