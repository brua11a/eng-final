from datetime import date
from typing import List, Optional
from pydantic import BaseModel


class TeacherCreateRequest(BaseModel):
    name: str
    surname: str
    phone: Optional[str] = None
    degree: str
    photo: Optional[str] = None
    working_since: date
    faculty_id: int


class TeacherCreateResponse(BaseModel):
    idx: str
    name: str
    surname: str
    phone: Optional[str] = None
    degree: str
    photo: Optional[str] = None
    working_since: date
    faculty_id: int
    err: Optional[str] = None


class TeacherCatalogueItem(BaseModel):
    idx: str
    name: str
    surname: str
    phone: Optional[str] = None
    degree: str
    photo: Optional[str] = None
    working_since: date
    faculty: str  # hydrated from WORKS_AT, not faculty_id


class TeacherCatalogueResponse(BaseModel):
    teachers: List[TeacherCatalogueItem]


class TeacherFindRequest(BaseModel):
    name: str


class TeacherFindResponse(BaseModel):
    teachers: List[TeacherCatalogueItem]


class TeacherDetailRequest(BaseModel):
    idx: str


class GroupAndCourse(BaseModel):
    course_code: str
    g_type: str
    group_num: int


class TeacherDetailResponse(BaseModel):
    degree: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    groups: List[GroupAndCourse]