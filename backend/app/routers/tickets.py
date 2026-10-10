from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Category, Computer, Priority, Technician, Ticket, User
from app.schemas import TicketAssign, TicketCreate, TicketOut, TicketStatusChange

router = APIRouter(prefix="/tickets", tags=["Tickets"])

LOAD_OPTIONS = (
    selectinload(Ticket.priority),
    selectinload(Ticket.category),
    selectinload(Ticket.creator),
    selectinload(Ticket.technician).selectinload(Technician.user),
)

ALLOWED_TRANSITIONS = {
    "Abierto": {"En progreso"},
    "En progreso": {"Pendiente", "Resuelto"},
    "Pendiente": {"En progreso"},
    "Resuelto": {"Cerrado", "En progreso"},
    "Cerrado": set(),
}


def to_out(ticket: Ticket) -> TicketOut:
    """Convierte un Ticket en su respuesta, añadiendo los nombres."""
    data = {name: getattr(ticket, name) for name in TicketOut.model_fields if hasattr(ticket, name)}
    return TicketOut(
        **data,
        priority_name=ticket.priority.name,
        category_name=ticket.category.name,
        creator_name=ticket.creator.full_name,
        technician_name=ticket.technician.user.full_name if ticket.technician else None,
    )


def get_or_404(db: Session, ticket_id: int) -> Ticket:
    ticket = db.scalars(
        select(Ticket).where(Ticket.id == ticket_id).options(*LOAD_OPTIONS)
    ).first()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return ticket


def check_references(db: Session, data: TicketCreate) -> None:
    if db.get(Priority, data.priority_id) is None:
        raise HTTPException(status_code=422, detail="La prioridad indicada no existe")
    if db.get(Category, data.category_id) is None:
        raise HTTPException(status_code=422, detail="La categoría indicada no existe")
    creator = db.get(User, data.created_by)
    if creator is None:
        raise HTTPException(status_code=422, detail="El usuario creador no existe")
    if not creator.is_active:
        raise HTTPException(status_code=422, detail="El usuario creador está desactivado")
    if data.computer_id is not None and db.get(Computer, data.computer_id) is None:
        raise HTTPException(status_code=422, detail="El equipo indicado no existe")


@router.get("", response_model=list[TicketOut])
def list_tickets(db: Session = Depends(get_db)):
    tickets = db.scalars(
        select(Ticket).options(*LOAD_OPTIONS).order_by(Ticket.created_at.desc())
    ).all()
    return [to_out(t) for t in tickets]


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    return to_out(get_or_404(db, ticket_id))


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(data: TicketCreate, db: Session = Depends(get_db)):
    check_references(db, data)
    ticket = Ticket(**data.model_dump(), status="Abierto")
    db.add(ticket)
    db.commit()
    return to_out(get_or_404(db, ticket.id))


@router.patch("/{ticket_id}/assign", response_model=TicketOut)
def assign_ticket(ticket_id: int, data: TicketAssign, db: Session = Depends(get_db)):
    ticket = get_or_404(db, ticket_id)
    if ticket.status in ("Resuelto", "Cerrado"):
        raise HTTPException(
            status_code=409,
            detail=f"No se puede asignar un ticket en estado '{ticket.status}'",
        )
    technician = db.scalars(
        select(Technician)
        .where(Technician.id == data.technician_id)
        .options(selectinload(Technician.user))
    ).first()
    if technician is None:
        raise HTTPException(status_code=422, detail="El técnico indicado no existe")
    if not technician.is_active or not technician.user.is_active:
        raise HTTPException(status_code=422, detail="El técnico indicado está inactivo")
    ticket.assigned_to = technician.id
    db.commit()
    return to_out(get_or_404(db, ticket_id))


@router.patch("/{ticket_id}/status", response_model=TicketOut)
def change_status(ticket_id: int, data: TicketStatusChange, db: Session = Depends(get_db)):
    ticket = get_or_404(db, ticket_id)
    current, new = ticket.status, data.status

    if new == current:
        raise HTTPException(status_code=409, detail=f"El ticket ya está en estado '{current}'")

    allowed = ALLOWED_TRANSITIONS[current]
    if new not in allowed:
        options = ", ".join(sorted(allowed)) or "ninguno (estado final)"
        raise HTTPException(
            status_code=409,
            detail=f"Transición no permitida: '{current}' -> '{new}'. Permitidos desde '{current}': {options}",
        )

    if new == "En progreso" and ticket.assigned_to is None:
        raise HTTPException(
            status_code=409,
            detail="El ticket debe tener un técnico asignado antes de pasar a 'En progreso'",
        )

    if new == "Resuelto":
        if not (data.diagnosis or ticket.diagnosis):
            raise HTTPException(status_code=422, detail="Para resolver hay que registrar el diagnóstico")
        if not (data.solution or ticket.solution):
            raise HTTPException(status_code=422, detail="Para resolver hay que registrar la solución")

    if data.diagnosis is not None:
        ticket.diagnosis = data.diagnosis
    if data.solution is not None:
        ticket.solution = data.solution

    if new == "Resuelto":
        now = datetime.now(timezone.utc)
        ticket.resolved_at = now
        seconds = (now - ticket.created_at).total_seconds()
        ticket.resolution_minutes = max(0, round(seconds / 60))
    elif current == "Resuelto" and new == "En progreso":
        ticket.resolved_at = None
        ticket.resolution_minutes = None

    ticket.status = new
    db.commit()
    return to_out(get_or_404(db, ticket_id))
