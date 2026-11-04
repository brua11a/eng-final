from datetime import date, time
from typing import List, Optional
from pydantic import BaseModel

from .generic import TeacherNameRef


class GroupTypeCreateRequest(BaseModel):
    subject_code: str
    g_type: str
    weight: float


class GroupTypeCreateResponse(BaseModel):
    id: str
    subject_code: str
    g_type: str
    weight: float
    err: Optional[str] = None


class GroupCreateRequest(BaseModel):
    weekday: int
    g_type: str
    number: int
    pnp: str
    capacity: int
    start_hr: time
    end_time: time
    subject_code: str
    room_id: str


class GroupCreateResponse(BaseModel):
    id: str
    weekday: int
    g_type: str
    number: int
    pnp: str
    capacity: int
    start_hr: time
    end_time: time
    subject_code: str
    room_id: str
    err: Optional[str] = None


class TeacherAssignRequest(BaseModel):
    teacher_idx: str
    group_id: str


class TeacherAssignResponse(BaseModel):
    teacher_idx: str
    group_id: str
    err: Optional[str] = None


class GroupNested(BaseModel):
    id: str
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
    group_id: str


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
