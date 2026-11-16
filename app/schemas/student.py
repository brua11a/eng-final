from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

from app.schemas.grades import check_grade


class StudentCreateRequest(BaseModel):
    idx: str = Field(pattern=r"^[0-9]+$")
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


class StudentDetailResponse(BaseModel):
    idx: str
    name: str
    surname: str
    phone: str
    photo: Optional[str] = None
    joined: datetime
    avg_grade: Optional[float] = None
    term_ids: list[str] = Field(default_factory=list)


class StudentInGroup(BaseModel):
    idx: str
    name: str
    surname: str
    phone: str
    photo: Optional[str] = None
    joined: datetime
    grade: Optional[float] = None


class StudentsInGroupResponse(BaseModel):
    students: List[StudentInGroup]


class SetGroupGradeRequest(BaseModel):
    grade: float

    @field_validator("grade")
    @classmethod
    def grade_on_scale(cls, value: float) -> float:
        return check_grade(value)


class SetGroupGradeResponse(BaseModel):
    group_id: str
    student_idx: str
    grade: float