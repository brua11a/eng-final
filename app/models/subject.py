from typing import Optional
from pydantic import BaseModel

class Subject(BaseModel):
    code: str
    name: str
    ects: Optional[int] = None