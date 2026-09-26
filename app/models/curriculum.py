from pydantic import BaseModel

class Curriculum(BaseModel):
    id: int
    name: str
    faculty_id: int