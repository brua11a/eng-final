from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class Student(BaseModel):
    idx: str
    name: str
    surname: str
    phone: Optional[str] = None
    photo: Optional[str] = None
    joined: datetime