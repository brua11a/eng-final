from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

from app.schemas.grades import check_grade


class OpinionCreateRequest(BaseModel):
    grade: float
    content: Optional[str] = Field(default=None, max_length=1000)
    group_id: str
    teacher_idx: str

    @field_validator("grade")
    @classmethod
    def grade_on_scale(cls, value: float) -> float:
        return check_grade(value)


class OpinionCreateResponse(BaseModel):
    id: Optional[str] = None
    grade: float
    content: Optional[str] = None
    submit: Optional[datetime] = None
    group_id: str
    teacher_idx: str


class OpinionItem(BaseModel):
    id: str
    grade: float
    content: Optional[str] = None
    submit: datetime
    group_id: str
    course_code: str
    course_name: str
    g_type: str
    cycle: str
    teacher_idx: str
    teacher: str


class OpinionListResponse(BaseModel):
    opinions: List[OpinionItem]
    avg_grade: Optional[float] = None
