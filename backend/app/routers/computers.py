from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Computer, Department, User
from app.schemas import ComputerCreate, ComputerOut, ComputerUpdate

router = APIRouter(prefix="/computers", tags=["Computers"])

DUPLICATE_MSG = "Ya existe un equipo con ese hostname o número de serie"


def get_or_404(db: Session, computer_id: int) -> Computer:
    computer = db.get(Computer, computer_id)
    if computer is None:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    return computer


def check_references(db: Session, assigned_to: int | None, department_id: int | None) -> None:
    if assigned_to is not None and db.get(User, assigned_to) is None:
        raise HTTPException(status_code=422, detail="El usuario indicado no existe")
    if department_id is not None and db.get(Department, department_id) is None:
        raise HTTPException(status_code=422, detail="El departamento indicado no existe")


@router.get("", response_model=list[ComputerOut])
def list_computers(db: Session = Depends(get_db)):
    return db.scalars(select(Computer).order_by(Computer.id)).all()


@router.get("/{computer_id}", response_model=ComputerOut)
def get_computer(computer_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, computer_id)


@router.post("", response_model=ComputerOut, status_code=status.HTTP_201_CREATED)
def create_computer(data: ComputerCreate, db: Session = Depends(get_db)):
    check_references(db, data.assigned_to, data.department_id)
    computer = Computer(**data.model_dump())
    db.add(computer)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=DUPLICATE_MSG)
    db.refresh(computer)
    return computer


@router.patch("/{computer_id}", response_model=ComputerOut)
def update_computer(computer_id: int, data: ComputerUpdate, db: Session = Depends(get_db)):
    computer = get_or_404(db, computer_id)
    changes = data.model_dump(exclude_unset=True)
    check_references(db, changes.get("assigned_to"), changes.get("department_id"))
    for field, value in changes.items():
        setattr(computer, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=DUPLICATE_MSG)
    db.refresh(computer)
    return computer


@router.delete("/{computer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_computer(computer_id: int, db: Session = Depends(get_db)):
    computer = get_or_404(db, computer_id)
    db.delete(computer)
    db.commit()
