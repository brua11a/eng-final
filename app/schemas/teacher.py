from datetime import date
from typing import List, Optional
from pydantic import BaseModel


class TeacherCreateRequest(BaseModel):
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


class GroupAndCourse(BaseModel):
    group_id: str
    course_code: str
    course_name: str = ""
    g_type: str
    group_num: int
    academic_cycle: str = ""


class TeacherDetailResponse(BaseModel):
    degree: str
    name: str
    phone: str
    email: Optional[str] = None
    groups: List[GroupAndCourse]