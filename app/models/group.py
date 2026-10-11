from datetime import time
from pydantic import BaseModel

class Group(BaseModel):
    id: int
    weekday: int
    g_type: str
    number: int
    pnp: str
    capacity: int
    start_hr: time
    end_time: time
    subject_code: str
    room_id: int