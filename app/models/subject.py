from pydantic import BaseModel

class Subject(BaseModel):
    code: str
    name: str
    ects: int