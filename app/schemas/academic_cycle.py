from typing import List, Optional
from pydantic import BaseModel


class AcademicCycleCreateRequest(BaseModel):
    year: str
    season: str


class AcademicCycleCreateResponse(BaseModel):
    id: int
    year: str
    season: str
    err: Optional[str] = None

class MyAcademicCycleItem(BaseModel):
    id: int
    year: str
    season: str


class MyAcademicCyclesResponse(BaseModel):
    cycles: List[MyAcademicCycleItem]


class MyAcademicCycleDetailRequest(BaseModel):
    cycle_id: int


class MyAcademicCycleDetailResponse(BaseModel):
    id: int
    year: str
    season: str
    # TODO: subjects/groups?