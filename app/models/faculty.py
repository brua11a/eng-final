from pydantic import BaseModel

class Faculty(BaseModel):
    id: int
    name: str
    full_name: str