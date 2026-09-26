from typing import Optional
from pydantic import BaseModel


class OkResponse(BaseModel):
    ok: bool
    err: Optional[str] = None


class TeacherNameRef(BaseModel):
    id: str
    name: str