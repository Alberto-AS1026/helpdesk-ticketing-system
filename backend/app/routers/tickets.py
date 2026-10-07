from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Category, Computer, Priority, Technician, Ticket, User
from app.schemas import TicketCreate, TicketOut

router = APIRouter(prefix="/tickets", tags=["Tickets"])

LOAD_OPTIONS = (
    selectinload(Ticket.priority),
    selectinload(Ticket.category),
    selectinload(Ticket.creator),
    selectinload(Ticket.technician).selectinload(Technician.user),
)


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
