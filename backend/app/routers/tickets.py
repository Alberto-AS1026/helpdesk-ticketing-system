from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Category, Computer, Priority, Technician, Ticket, TicketComment, User
from app.schemas import (
    CommentCreate,
    CommentOut,
    TicketAssign,
    TicketCreate,
    TicketOut,
    TicketResolutionUpdate,
    TicketStatusChange,
)

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


def comment_to_out(comment: TicketComment) -> CommentOut:
    return CommentOut(
        id=comment.id,
        ticket_id=comment.ticket_id,
        user_id=comment.user_id,
        author_name=comment.author.full_name,
        comment=comment.comment,
        created_at=comment.created_at,
    )


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


@router.patch("/{ticket_id}/resolution", response_model=TicketOut)
def update_resolution(ticket_id: int, data: TicketResolutionUpdate, db: Session = Depends(get_db)):
    ticket = get_or_404(db, ticket_id)
    if ticket.status == "Cerrado":
        raise HTTPException(status_code=409, detail="No se puede modificar un ticket cerrado")
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Indica al menos diagnosis o solution")
    for field, value in changes.items():
        setattr(ticket, field, value)
    db.commit()
    return to_out(get_or_404(db, ticket_id))


@router.get("/{ticket_id}/comments", response_model=list[CommentOut])
def list_comments(ticket_id: int, db: Session = Depends(get_db)):
    get_or_404(db, ticket_id)
    comments = db.scalars(
        select(TicketComment)
        .where(TicketComment.ticket_id == ticket_id)
        .options(selectinload(TicketComment.author))
        .order_by(TicketComment.created_at, TicketComment.id)
    ).all()
    return [comment_to_out(c) for c in comments]


@router.post(
    "/{ticket_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
def add_comment(ticket_id: int, data: CommentCreate, db: Session = Depends(get_db)):
    ticket = get_or_404(db, ticket_id)
    if ticket.status == "Cerrado":
        raise HTTPException(status_code=409, detail="No se puede comentar un ticket cerrado")
    author = db.get(User, data.author_id)
    if author is None:
        raise HTTPException(status_code=422, detail="El autor indicado no existe")
    if not author.is_active:
        raise HTTPException(status_code=422, detail="El autor indicado está desactivado")
    comment = TicketComment(ticket_id=ticket_id, user_id=author.id, comment=data.comment)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment_to_out(comment)
