from typing import List, Optional
from pydantic import BaseModel


class CurriculumCreateRequest(BaseModel):
    name: str
    faculty_id: int


class CurriculumCreateResponse(BaseModel):
    id: int
    name: str
    faculty_id: int
    err: Optional[str] = None


class CurriculumCatalogueItem(BaseModel):
    id: int
    name: str
    faculty_id: int


class CurriculumCatalogueResponse(BaseModel):
    curricula: List[CurriculumCatalogueItem]


class CurriculumFindRequest(BaseModel):
    name: str


class CurriculumFindResponse(BaseModel):
    curricula: List[CurriculumCatalogueItem]