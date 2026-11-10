from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class OpinionCreateRequest(BaseModel):
    grade: float
    content: Optional[str] = None
    submit: datetime
    group_id: str
    teacher_idx: str
    student_idx: Optional[str] = None
    # ^ required only when the caller is admin (WRITES needs a Student).
    #   When caller is student, derive from session and ignore/reject
    #   a client-supplied value to prevent submitting on someone else's behalf.


class OpinionCreateResponse(BaseModel):
    id: Optional[str] = None
    grade: float
    content: Optional[str] = None
    submit: datetime
    group_id: str
    teacher_idx: str
    err: Optional[str] = None


class OpinionListRequest(BaseModel):
    teacher_idx: Optional[str] = None
    group_id: Optional[str] = None


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
