from datetime import date
from typing import Optional
from pydantic import BaseModel

class Teacher(BaseModel):
    idx: str
    name: str
    surname: str
    phone: Optional[str] = None
    degree: str
    photo: Optional[str] = None
    working_since: date
    faculty_id: int