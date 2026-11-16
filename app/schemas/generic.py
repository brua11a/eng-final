from pydantic import BaseModel


class TeacherNameRef(BaseModel):
    id: str
    name: str