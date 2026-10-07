from pydantic import BaseModel, ConfigDict, Field


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
