from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class Student(BaseModel):
    idx: str
    name: str
    surname: str
    phone: Optional[str] = None
    photo: Optional[str] = None
    joined: datetime
    avg_grade: Optional[float] = None
    term_ids: list[int] = Field(default_factory=list)