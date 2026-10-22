from datetime import time
from typing import List, Optional
from pydantic import BaseModel


class RegisteredGroup(BaseModel):
    course_code: str
    course_name: str
    g_type: str
    number: int
    weekday: int
    start: time
    end: time
    room: Optional[str] = None
    cycle: Optional[str] = None


class DashboardResponse(BaseModel):
    groups: List[RegisteredGroup]
