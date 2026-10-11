from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class Opinion(BaseModel):
    id: int
    grade: float
    content: Optional[str] = None
    submit: datetime
    student_idx: str
    group_id: int
