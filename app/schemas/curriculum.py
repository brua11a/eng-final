from typing import List, Optional
from pydantic import BaseModel


class CurriculumCreateRequest(BaseModel):
    programme_id: int
    intake_year: str


class CurriculumCreateResponse(BaseModel):
    id: int
    programme_id: int
    intake_year: str
    err: Optional[str] = None


class CurriculumCatalogueItem(BaseModel):
    id: int
    programme_id: int
    name: str
    intake_year: str


class CurriculumCatalogueResponse(BaseModel):
    curricula: List[CurriculumCatalogueItem]


class CurriculumFindRequest(BaseModel):
    name: str


class CurriculumFindResponse(BaseModel):
    curricula: List[CurriculumCatalogueItem]
