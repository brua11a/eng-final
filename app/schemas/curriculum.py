from typing import List, Optional
from pydantic import BaseModel


class CurriculumCreateRequest(BaseModel):
    programme_id: str
    intake_year: str


class CurriculumCreateResponse(BaseModel):
    id: str
    programme_id: str
    intake_year: str
    err: Optional[str] = None


class CurriculumCatalogueItem(BaseModel):
    id: str
    programme_id: str
    name: str
    intake_year: str


class CurriculumCatalogueResponse(BaseModel):
    curricula: List[CurriculumCatalogueItem]


class ProgrammeItem(BaseModel):
    id: str
    name: str
    faculty_id: str


class ProgrammeListResponse(BaseModel):
    programmes: List[ProgrammeItem]
