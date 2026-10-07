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
