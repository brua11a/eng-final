from typing import List, Optional
from pydantic import BaseModel


class FacultyCreateRequest(BaseModel):
    name: str
    full_name: str


class FacultyCreateResponse(BaseModel):
    id: str
    name: str
    full_name: str
    err: Optional[str] = None


class FacultyItem(BaseModel):
    id: str
    name: str
    full_name: str


class FacultyListResponse(BaseModel):
    faculties: List[FacultyItem]