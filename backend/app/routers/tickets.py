from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import STAFF, get_current_user, require_roles
from app.models import (
    Category,
    Computer,
    Priority,
    Technician,
    Ticket,
    TicketComment,
    TicketHistory,
    User,
)
from app.schemas import (
    CommentCreate,
    CommentOut,
    HistoryOut,
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

ALLOWED_TRANSITIONS = {
    "Abierto": {"En progreso"},
    "En progreso": {"Pendiente", "Resuelto"},
    "Pendiente": {"En progreso"},
    "Resuelto": {"Cerrado", "En progreso"},
    "Cerrado": set(),
}


# ---------- Funciones auxiliares ----------

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


def get_visible(db: Session, ticket_id: int, user: User) -> Ticket:
    """Un usuario normal solo ve sus tickets; si no son suyos, responde 404."""
    ticket = get_or_404(db, ticket_id)
    if user.role == "user" and ticket.created_by != user.id:
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


def history_to_out(entry: TicketHistory) -> HistoryOut:
    return HistoryOut(
        id=entry.id,
        ticket_id=entry.ticket_id,
        changed_by=entry.changed_by,
        user_name=entry.user.full_name,
        field_name=entry.field_name,
        old_value=entry.old_value,
        new_value=entry.new_value,
        changed_at=entry.changed_at,
    )


def log_change(db: Session, ticket_id: int, user_id: int, field: str, old, new) -> None:
    """Añade una entrada al historial si el valor ha cambiado (se guarda con el commit)."""
    old_s = None if old is None else str(old)
    new_s = None if new is None else str(new)
    if old_s == new_s:
        return
    db.add(TicketHistory(
        ticket_id=ticket_id, changed_by=user_id,
        field_name=field, old_value=old_s, new_value=new_s,
    ))


def check_references(db: Session, data: TicketCreate) -> None:
    if db.get(Priority, data.priority_id) is None:
        raise HTTPException(status_code=422, detail="La prioridad indicada no existe")
    if db.get(Category, data.category_id) is None:
        raise HTTPException(status_code=422, detail="La categoría indicada no existe")
    if data.computer_id is not None and db.get(Computer, data.computer_id) is None:
        raise HTTPException(status_code=422, detail="El equipo indicado no existe")


# ---------- Tickets ----------

@router.get("", response_model=list[TicketOut])
def list_tickets(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(Ticket).options(*LOAD_OPTIONS).order_by(Ticket.created_at.desc())
    if user.role == "user":
        query = query.where(Ticket.created_by == user.id)
    return [to_out(t) for t in db.scalars(query).all()]


@router.get("/{ticket_id}", response_model=TicketOut)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return to_out(get_visible(db, ticket_id, user))


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(
    data: TicketCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    check_references(db, data)
    ticket = Ticket(**data.model_dump(), created_by=user.id, status="Abierto")
    db.add(ticket)
    db.flush()  # asigna el id sin cerrar la transacción
    log_change(db, ticket.id, user.id, "creado", None, "Abierto")
    db.commit()
    return to_out(get_or_404(db, ticket.id))


@router.patch("/{ticket_id}/assign", response_model=TicketOut)
def assign_ticket(
    ticket_id: int,
    data: TicketAssign,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*STAFF)),
):
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
    log_change(db, ticket.id, actor.id, "assigned_to", ticket.assigned_to, technician.id)
    ticket.assigned_to = technician.id
    db.commit()
    return to_out(get_or_404(db, ticket_id))


@router.patch("/{ticket_id}/status", response_model=TicketOut)
def change_status(
    ticket_id: int,
    data: TicketStatusChange,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*STAFF)),
):
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
        log_change(db, ticket.id, actor.id, "diagnosis", ticket.diagnosis, data.diagnosis)
        ticket.diagnosis = data.diagnosis
    if data.solution is not None:
        log_change(db, ticket.id, actor.id, "solution", ticket.solution, data.solution)
        ticket.solution = data.solution

    if new == "Resuelto":
        now = datetime.now(timezone.utc)
        ticket.resolved_at = now
        seconds = (now - ticket.created_at).total_seconds()
        ticket.resolution_minutes = max(0, round(seconds / 60))
    elif current == "Resuelto" and new == "En progreso":
        ticket.resolved_at = None
        ticket.resolution_minutes = None

    log_change(db, ticket.id, actor.id, "status", current, new)
    ticket.status = new
    db.commit()
    return to_out(get_or_404(db, ticket_id))


@router.patch("/{ticket_id}/resolution", response_model=TicketOut)
def update_resolution(
    ticket_id: int,
    data: TicketResolutionUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles(*STAFF)),
):
    ticket = get_or_404(db, ticket_id)
    if ticket.status == "Cerrado":
        raise HTTPException(status_code=409, detail="No se puede modificar un ticket cerrado")
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Indica al menos diagnosis o solution")
    for field, value in changes.items():
        log_change(db, ticket.id, actor.id, field, getattr(ticket, field), value)
        setattr(ticket, field, value)
    db.commit()
    return to_out(get_or_404(db, ticket_id))


# ---------- Comentarios ----------

@router.get("/{ticket_id}/comments", response_model=list[CommentOut])
def list_comments(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_visible(db, ticket_id, user)
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
def add_comment(
    ticket_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ticket = get_visible(db, ticket_id, user)
    if ticket.status == "Cerrado":
        raise HTTPException(status_code=409, detail="No se puede comentar un ticket cerrado")
    comment = TicketComment(ticket_id=ticket_id, user_id=user.id, comment=data.comment)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment_to_out(comment)


# ---------- Historial ----------

@router.get("/{ticket_id}/history", response_model=list[HistoryOut])
def get_history(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_visible(db, ticket_id, user)
    entries = db.scalars(
        select(TicketHistory)
        .where(TicketHistory.ticket_id == ticket_id)
        .options(selectinload(TicketHistory.user))
        .order_by(TicketHistory.changed_at, TicketHistory.id)
    ).all()
    return [history_to_out(e) for e in entries]
