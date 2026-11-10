from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

GRADE_SCALE = (2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0)


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

    @field_validator("grade")
    @classmethod
    def grade_on_scale(cls, value: float) -> float:
        if value not in GRADE_SCALE:
            raise ValueError(f"grade must be one of {', '.join(map(str, GRADE_SCALE))}")
        return value


class SetGroupGradeResponse(BaseModel):
    group_id: str
    student_idx: str
    grade: float
    err: Optional[str] = None