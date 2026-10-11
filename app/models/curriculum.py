from pydantic import BaseModel

class Curriculum(BaseModel):
    id: int
    name: str
    intake_year: str
    faculty_id: int
