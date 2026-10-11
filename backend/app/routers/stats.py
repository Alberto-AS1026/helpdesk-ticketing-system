from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Category, Priority, Technician, Ticket, User
from app.schemas import (
    CountItem,
    DayCount,
    StatsOut,
    StatsSummary,
    TechnicianLoad,
)

router = APIRouter(prefix="/stats", tags=["Stats"])

STATUS_ORDER = ["Abierto", "En progreso", "Pendiente", "Resuelto", "Cerrado"]
ACTIVE_STATUSES = ("Abierto", "En progreso", "Pendiente")


@router.get("", response_model=StatsOut)
def get_stats(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    # Resumen general: una sola consulta con agregados condicionales
    row = db.execute(
        select(
            func.count(Ticket.id),
            func.count(case((Ticket.status.in_(ACTIVE_STATUSES), 1))),
            func.count(case((Ticket.assigned_to.is_(None), 1))),
            func.count(case((Ticket.status.in_(("Resuelto", "Cerrado")), 1))),
            func.avg(Ticket.resolution_minutes),
        )
    ).one()
    summary = StatsSummary(
        total_tickets=row[0],
        open_tickets=row[1],
        unassigned_tickets=row[2],
        resolved_tickets=row[3],
        avg_resolution_minutes=round(float(row[4]), 1) if row[4] is not None else None,
    )

    # Por estado (en el orden del flujo, con ceros incluidos)
    status_counts = dict(
        db.execute(select(Ticket.status, func.count(Ticket.id)).group_by(Ticket.status)).all()
    )
    by_status = [CountItem(label=s, count=status_counts.get(s, 0)) for s in STATUS_ORDER]

    # Por prioridad: LEFT JOIN para que aparezcan las que tienen 0
    by_priority = [
        CountItem(label=name, count=count)
        for name, count in db.execute(
            select(Priority.name, func.count(Ticket.id))
            .select_from(Priority)
            .outerjoin(Ticket, Ticket.priority_id == Priority.id)
            .group_by(Priority.id, Priority.name, Priority.level)
            .order_by(Priority.level.desc())
        ).all()
    ]

    # Por categoría
    by_category = [
        CountItem(label=name, count=count)
        for name, count in db.execute(
            select(Category.name, func.count(Ticket.id))
            .select_from(Category)
            .outerjoin(Ticket, Ticket.category_id == Category.id)
            .group_by(Category.id, Category.name)
            .order_by(func.count(Ticket.id).desc(), Category.name)
        ).all()
    ]

    # Carga por técnico: abiertos y totales
    technician_load = [
        TechnicianLoad(technician_id=tid, name=name, open_tickets=open_, total_tickets=total)
        for tid, name, open_, total in db.execute(
            select(
                Technician.id,
                User.full_name,
                func.count(case((Ticket.status.in_(ACTIVE_STATUSES), 1))),
                func.count(Ticket.id),
            )
            .select_from(Technician)
            .join(User, User.id == Technician.user_id)
            .outerjoin(Ticket, Ticket.assigned_to == Technician.id)
            .group_by(Technician.id, User.full_name)
            .order_by(func.count(case((Ticket.status.in_(ACTIVE_STATUSES), 1))).desc())
        ).all()
    ]

    # Tickets creados por día en los últimos N días
    day_col = func.date(Ticket.created_at)
    per_day = [
        DayCount(day=str(day), count=count)
        for day, count in db.execute(
            select(day_col, func.count(Ticket.id))
            .where(Ticket.created_at >= func.now() - func.make_interval(0, 0, 0, days))
            .group_by(day_col)
            .order_by(day_col)
        ).all()
    ]

    return StatsOut(
        summary=summary,
        by_status=by_status,
        by_priority=by_priority,
        by_category=by_category,
        technician_load=technician_load,
        per_day=per_day,
    )
