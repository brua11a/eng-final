from pydantic import BaseModel

class AcademicCycle(BaseModel):
    id: int
    year: str
    season: str
