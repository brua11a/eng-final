from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class StudentCreateRequest(BaseModel):
    name: str
    surname: str
    phone: str
    photo: Optional[str] = None
    joined: datetime
    programme: str
    term_id: Optional[str] = None


class StudentCreateResponse(BaseModel):
    idx: str
    name: str
    surname: str
    phone: str
    photo: Optional[str] = None
    joined: datetime
    err: Optional[str] = None


class StudentDetailRequest(BaseModel):
    student_idx: str


class StudentDetailResponse(BaseModel):
    idx: str
    name: str
    surname: str
    phone: str
    photo: Optional[str] = None
    joined: datetime
    avg_grade: Optional[float] = None
    term_ids: list[str] = Field(default_factory=list)
    err: Optional[str] = None


class StudentInGroup(BaseModel):
    idx: str
    name: str
    surname: str
    phone: str
    photo: Optional[str] = None
    joined: datetime
    grade: Optional[float] = None


class StudentsInGroupRequest(BaseModel):
    group_id: str


class StudentsInGroupResponse(BaseModel):
    students: List[StudentInGroup]


class SetGroupGradeRequest(BaseModel):
    group_id: str
    student_idx: str
    grade: float


class SetGroupGradeResponse(BaseModel):
    group_id: str
    student_idx: str
    grade: float
    err: Optional[str] = None