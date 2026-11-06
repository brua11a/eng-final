from datetime import time
from typing import List, Optional
from pydantic import BaseModel, Field


class AcademicCycleCreateRequest(BaseModel):
    year: str
    season: str


class AcademicCycleCreateResponse(BaseModel):
    id: str
    year: str
    season: str
    err: Optional[str] = None

class MyAcademicCycleItem(BaseModel):
    id: str
    year: str
    season: str


class MyAcademicCyclesResponse(BaseModel):
    cycles: List[MyAcademicCycleItem]


class AcademicCycleListResponse(BaseModel):
    cycles: List[MyAcademicCycleItem]


class MyAcademicCycleDetailRequest(BaseModel):
    cycle_id: str


class CycleSubjectGroup(BaseModel):
    id: str
    g_type: str
    number: int
    weekday: Optional[int] = None
    start: Optional[time] = None
    end: Optional[time] = None
    room: Optional[str] = None
    teacher: Optional[str] = None
    grade: Optional[float] = None


class CycleSubject(BaseModel):
    code: str
    name: str
    ects: Optional[int] = None
    groups: List[CycleSubjectGroup] = Field(default_factory=list)


class MyAcademicCycleDetailResponse(BaseModel):
    id: str
    year: str
    season: str
    subjects: List[CycleSubject] = Field(default_factory=list)