from pydantic import BaseModel

class Programme(BaseModel):
    id: int
    name: str
    faculty_id: int
