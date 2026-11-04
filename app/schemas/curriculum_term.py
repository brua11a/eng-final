from typing import Optional
from pydantic import BaseModel


class CurriculumTermCreateRequest(BaseModel):
    sem: int
    curriculum_id: str
    cycle_id: Optional[str] = None


class CurriculumTermCreateResponse(BaseModel):
    id: str
    sem: int
    curriculum_id: str
    cycle_id: Optional[str] = None
    err: Optional[str] = None
