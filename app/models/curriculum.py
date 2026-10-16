from pydantic import BaseModel

class Curriculum(BaseModel):
    id: int
    intake_year: str
    programme_id: int
