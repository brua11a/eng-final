from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class OpinionCreateRequest(BaseModel):
    grade: float
    content: Optional[str] = None
    submit: datetime
    group_id: str
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
    err: Optional[str] = None
