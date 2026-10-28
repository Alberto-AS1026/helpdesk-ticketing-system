from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Departamentos ----------

class DepartmentCreate(BaseModel):
    """Datos que el cliente envía para crear."""
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None


class DepartmentUpdate(BaseModel):
    """Datos para modificar: todos opcionales."""
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = None


class DepartmentOut(BaseModel):
    """Datos que la API devuelve."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None


# ---------- Categorías ----------

class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


# ---------- Prioridades ----------

class PriorityCreate(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    level: int = Field(ge=1, le=4)


class PriorityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=50)
    level: int | None = Field(default=None, ge=1, le=4)


class PriorityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    level: int


# ---------- Usuarios y técnicos ----------

Role = Literal["user", "technician", "admin"]
Level = Literal["N1", "N2", "N3"]


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: Role = "user"
    department_id: int | None = None


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=72)
    role: Role | None = None
    department_id: int | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    role: str
    department_id: int | None
    is_active: bool
    created_at: datetime


class TechnicianCreate(BaseModel):
    user_id: int
    specialty: str | None = Field(default=None, max_length=100)
    level: Level = "N1"


class TechnicianUpdate(BaseModel):
    specialty: str | None = Field(default=None, max_length=100)
    level: Level | None = None
    is_active: bool | None = None


class TechnicianOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    specialty: str | None
    level: str
    is_active: bool


# ---------- Equipos ----------

class ComputerCreate(BaseModel):
    hostname: str = Field(min_length=2, max_length=100)
    serial_number: str | None = Field(default=None, max_length=100)
    brand: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    os: str | None = Field(default=None, max_length=100)
    assigned_to: int | None = None
    department_id: int | None = None


class ComputerUpdate(BaseModel):
    hostname: str | None = Field(default=None, min_length=2, max_length=100)
    serial_number: str | None = Field(default=None, max_length=100)
    brand: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    os: str | None = Field(default=None, max_length=100)
    assigned_to: int | None = None
    department_id: int | None = None


class ComputerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    hostname: str
    serial_number: str | None
    brand: str | None
    model: str | None
    os: str | None
    assigned_to: int | None
    department_id: int | None
    created_at: datetime


# ---------- Tickets ----------

TicketStatus = Literal["Abierto", "En progreso", "Pendiente", "Resuelto", "Cerrado"]


class TicketCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5)
    priority_id: int
    category_id: int
    computer_id: int | None = None


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: str
    priority_id: int
    category_id: int
    created_by: int
    assigned_to: int | None
    computer_id: int | None
    diagnosis: str | None
    solution: str | None
    created_at: datetime
    resolved_at: datetime | None
    resolution_minutes: int | None
    priority_name: str
    category_name: str
    creator_name: str
    technician_name: str | None
    technician_user_id: int | None


class TicketAssign(BaseModel):
    technician_id: int


class TicketStatusChange(BaseModel):
    status: TicketStatus
    diagnosis: str | None = Field(default=None, min_length=3)
    solution: str | None = Field(default=None, min_length=3)


class TicketResolutionUpdate(BaseModel):
    diagnosis: str | None = Field(default=None, min_length=3)
    solution: str | None = Field(default=None, min_length=3)


# ---------- Comentarios e historial ----------

class CommentCreate(BaseModel):
    comment: str = Field(min_length=2)


class CommentOut(BaseModel):
    id: int
    ticket_id: int
    user_id: int
    author_name: str
    comment: str
    created_at: datetime


class HistoryOut(BaseModel):
    id: int
    ticket_id: int
    changed_by: int
    user_name: str
    field_name: str
    old_value: str | None
    new_value: str | None
    changed_at: datetime


# ---------- Chat ----------

class ChatContact(BaseModel):
    """Usuario con el que se puede abrir una conversación (sin email)."""
    id: int
    full_name: str
    role: str


class ConversationCreate(BaseModel):
    user_id: int


class ConversationOut(BaseModel):
    id: int
    other: ChatContact
    other_online: bool
    other_last_seen_at: datetime | None
    last_message: str | None
    last_message_at: datetime | None
    last_message_mine: bool
    last_message_read: bool  # el último mensaje es mío y la otra persona ya lo leyó
    unread: int


class ChatMessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    sender_id: int
    body: str
    created_at: datetime


class ChatSync(BaseModel):
    """Lo que la conversación abierta necesita en cada ciclo de polling."""
    messages: list[ChatMessageOut]
    other_last_read_id: int
    other_online: bool
    other_last_seen_at: datetime | None
    other_typing: bool


class ChatRead(BaseModel):
    last_read_id: int = Field(ge=0)


class UnreadOut(BaseModel):
    unread: int


# ---------- Autenticación ----------

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Paginación ----------

class TicketPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[TicketOut]


# ---------- Estadísticas ----------

class CountItem(BaseModel):
    label: str
    count: int


class TechnicianLoad(BaseModel):
    technician_id: int
    name: str
    open_tickets: int
    total_tickets: int


class DayCount(BaseModel):
    day: str
    count: int


class StatsSummary(BaseModel):
    total_tickets: int
    open_tickets: int
    unassigned_tickets: int
    resolved_tickets: int
    avg_resolution_minutes: float | None


class StatsOut(BaseModel):
    summary: StatsSummary
    by_status: list[CountItem]
    by_priority: list[CountItem]
    by_category: list[CountItem]
    technician_load: list[TechnicianLoad]
    per_day: list[DayCount]
