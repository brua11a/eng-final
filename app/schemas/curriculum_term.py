from typing import Optional
from pydantic import BaseModel


class CurriculumTermCreateRequest(BaseModel):
    sem: int
    curriculum_id: int


class CurriculumTermCreateResponse(BaseModel):
    id: int
    sem: int
    curriculum_id: int
    err: Optional[str] = None