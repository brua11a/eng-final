from typing import Optional
from pydantic import BaseModel

class CurriculumTerm(BaseModel):
    id: int
    sem: int
    curriculum_id: int
    cycle_id: Optional[int] = None
