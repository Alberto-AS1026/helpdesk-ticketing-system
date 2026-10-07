from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


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
    email: EmailStr
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


class TicketCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5)
    priority_id: int
    category_id: int
    created_by: int  # provisional hasta la Fase 5 (autenticación)
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
