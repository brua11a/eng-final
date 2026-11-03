from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class StudentCreateRequest(BaseModel):
    name: str
    surname: str
    phone: str
    photo: Optional[str] = None
    joined: datetime
    programme: int


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
    term_ids: list[int] = Field(default_factory=list)
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
    group_id: int


class StudentsInGroupResponse(BaseModel):
    students: List[StudentInGroup]


class SetGroupGradeRequest(BaseModel):
    group_id: int
    student_idx: str
    grade: float


class SetGroupGradeResponse(BaseModel):
    group_id: int
    student_idx: str
    grade: float
    err: Optional[str] = None