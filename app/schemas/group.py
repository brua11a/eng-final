from datetime import date, time
from typing import List, Optional
from pydantic import BaseModel

from .generic import TeacherNameRef


class GroupCreateRequest(BaseModel):
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


class GroupCreateResponse(BaseModel):
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
    err: Optional[str] = None


class TeacherAssignRequest(BaseModel):
    teacher_idx: str
    group_id: int


class TeacherAssignResponse(BaseModel):
    teacher_idx: str
    group_id: int
    err: Optional[str] = None


class GroupNested(BaseModel):
    id: int
    weekday: int
    g_type: str
    number: int
    pnp: str
    capacity: int
    start_hr: time
    end_time: time
    cycle: str
    room: str


class GroupTracked(GroupNested):
    filled: int


class GroupDetailRequest(BaseModel):
    code: str
    group_num: int


class ClassOccurrence(BaseModel):
    class_date: date
    class_start: time
    class_end: time
    building: str


class GroupDetailResponse(BaseModel):
    course_name: str
    g_type: str
    academic_cycle: str
    group_num: int
    building: str
    nearest_classes: List[ClassOccurrence]
    filled: int
    capacity: int
    teacher: TeacherNameRef