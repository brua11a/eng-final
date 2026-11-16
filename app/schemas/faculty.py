from typing import List
from pydantic import BaseModel


class FacultyCreateRequest(BaseModel):
    name: str
    full_name: str


class FacultyCreateResponse(BaseModel):
    id: str
    name: str
    full_name: str


class FacultyItem(BaseModel):
    id: str
    name: str
    full_name: str


class FacultyListResponse(BaseModel):
    faculties: List[FacultyItem]