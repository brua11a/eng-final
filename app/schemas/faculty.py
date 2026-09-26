from typing import Optional
from pydantic import BaseModel


class FacultyCreateRequest(BaseModel):
    name: str
    full_name: str


class FacultyCreateResponse(BaseModel):
    id: int
    name: str
    full_name: str
    err: Optional[str] = None