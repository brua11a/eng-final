from pydantic import BaseModel

class CurriculumTerm(BaseModel):
    id: int
    sem: int
    curriculum_id: int