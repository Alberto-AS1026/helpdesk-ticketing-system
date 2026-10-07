from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Priority
from app.schemas import PriorityCreate, PriorityOut, PriorityUpdate

router = APIRouter(prefix="/priorities", tags=["Priorities"])


def get_or_404(db: Session, priority_id: int) -> Priority:
    priority = db.get(Priority, priority_id)
    if priority is None:
        raise HTTPException(status_code=404, detail="Prioridad no encontrada")
    return priority


@router.get("", response_model=list[PriorityOut])
def list_priorities(db: Session = Depends(get_db)):
    return db.scalars(select(Priority).order_by(Priority.level)).all()


@router.get("/{priority_id}", response_model=PriorityOut)
def get_priority(priority_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, priority_id)


@router.post("", response_model=PriorityOut, status_code=status.HTTP_201_CREATED)
def create_priority(data: PriorityCreate, db: Session = Depends(get_db)):
    priority = Priority(**data.model_dump())
    db.add(priority)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una prioridad con ese nombre o nivel")
    db.refresh(priority)
    return priority


@router.patch("/{priority_id}", response_model=PriorityOut)
def update_priority(priority_id: int, data: PriorityUpdate, db: Session = Depends(get_db)):
    priority = get_or_404(db, priority_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(priority, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe una prioridad con ese nombre o nivel")
    db.refresh(priority)
    return priority


@router.delete("/{priority_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_priority(priority_id: int, db: Session = Depends(get_db)):
    priority = get_or_404(db, priority_id)
    db.delete(priority)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="No se puede borrar: tiene tickets asociados")
