from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers import categories, computers, departments, priorities, technicians, users

app = FastAPI(title="Help Desk API", version="0.5.0")

app.include_router(departments.router)
app.include_router(categories.router)
app.include_router(priorities.router)
app.include_router(users.router)
app.include_router(technicians.router)
app.include_router(computers.router)

@app.get("/health")
def health():
    """La API está viva."""
    return {"status": "ok"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    """La API puede hablar con la base de datos."""
    db.execute(text("SELECT 1"))
    return {"database": "ok"}
