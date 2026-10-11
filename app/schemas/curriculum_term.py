from typing import Optional
from pydantic import BaseModel


class CurriculumTermCreateRequest(BaseModel):
    sem: int
    curriculum_id: int
    cycle_id: Optional[int] = None


class CurriculumTermCreateResponse(BaseModel):
    id: int
    sem: int
    curriculum_id: int
    cycle_id: Optional[int] = None
    err: Optional[str] = None
