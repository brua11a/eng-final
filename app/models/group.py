from datetime import time
from pydantic import BaseModel, Field

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
    cycle_id: int
    room_id: int