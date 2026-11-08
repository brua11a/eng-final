from datetime import time
from typing import List, Optional
from pydantic import BaseModel


class GroupTeacher(BaseModel):
    idx: str
    name: str
    surname: str


class RegisteredGroup(BaseModel):
    group_id: str
    course_code: str
    course_name: str
    g_type: str
    number: int
    weekday: int
    start: time
    end: time
    pnp: str = ""
    room: Optional[str] = None
    cycle: Optional[str] = None
    teachers: List[GroupTeacher] = []


class DashboardResponse(BaseModel):
    groups: List[RegisteredGroup]
