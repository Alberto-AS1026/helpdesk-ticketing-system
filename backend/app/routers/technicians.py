from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Technician, User
from app.schemas import TechnicianCreate, TechnicianOut, TechnicianUpdate

router = APIRouter(prefix="/technicians", tags=["Technicians"])


def get_or_404(db: Session, technician_id: int) -> Technician:
    technician = db.get(Technician, technician_id)
    if technician is None:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")
    return technician


@router.get("", response_model=list[TechnicianOut])
def list_technicians(db: Session = Depends(get_db)):
    return db.scalars(select(Technician).order_by(Technician.id)).all()


@router.get("/{technician_id}", response_model=TechnicianOut)
def get_technician(technician_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, technician_id)


@router.post("", response_model=TechnicianOut, status_code=status.HTTP_201_CREATED)
def create_technician(data: TechnicianCreate, db: Session = Depends(get_db)):
    user = db.get(User, data.user_id)
    if user is None:
        raise HTTPException(status_code=422, detail="El usuario indicado no existe")
    if user.role == "user":
        raise HTTPException(
            status_code=422,
            detail="El usuario debe tener rol 'technician' o 'admin' para tener perfil técnico",
        )
    technician = Technician(**data.model_dump())
    db.add(technician)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Ese usuario ya tiene perfil técnico")
    db.refresh(technician)
    return technician


@router.patch("/{technician_id}", response_model=TechnicianOut)
def update_technician(technician_id: int, data: TechnicianUpdate, db: Session = Depends(get_db)):
    technician = get_or_404(db, technician_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(technician, field, value)
    db.commit()
    db.refresh(technician)
    return technician


@router.delete("/{technician_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_technician(technician_id: int, db: Session = Depends(get_db)):
    technician = get_or_404(db, technician_id)
    db.delete(technician)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="No se puede borrar: tiene tickets asignados. Desactívalo en su lugar",
        )
