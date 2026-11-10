from datetime import date, time
from typing import List, Optional
from pydantic import BaseModel, Field


class TeacherCreateRequest(BaseModel):
    idx: str = Field(pattern=r"^T[0-9]+$")
    name: str
    surname: str
    phone: str
    degree: str
    photo: Optional[str] = None
    working_since: date
    faculty_id: str


class TeacherCreateResponse(BaseModel):
    idx: str
    name: str
    surname: str
    phone: str
    degree: str
    photo: Optional[str] = None
    working_since: date
    faculty_id: str
    err: Optional[str] = None


class TeacherCatalogueItem(BaseModel):
    idx: str
    name: str
    surname: str
    phone: str
    degree: str
    photo: Optional[str] = None
    working_since: date
    faculty: str  # hydrated from WORKS_AT, not faculty_id


class TeacherCatalogueResponse(BaseModel):
    teachers: List[TeacherCatalogueItem]


class TeacherDetailRequest(BaseModel):
    idx: str


class TeachingGroupItem(BaseModel):
    group_id: str
    course_code: str
    course_name: str
    g_type: str
    group_num: int
    academic_cycle: str
    cycle_start: Optional[date] = None
    cycle_end: Optional[date] = None
    room: str = ""
    weekday: int = 0
    start: Optional[time] = None
    end: Optional[time] = None
    pnp: str = ""


class MyTeachingGroupsResponse(BaseModel):
    groups: List[TeachingGroupItem]


class TeacherDetailResponse(BaseModel):
    degree: str
    name: str
    phone: str
    email: Optional[str] = None
    groups: List[TeachingGroupItem]