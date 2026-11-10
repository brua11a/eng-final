from datetime import date, time
from typing import List, Optional
from pydantic import BaseModel

from .generic import TeacherNameRef


class GroupTypeCreateRequest(BaseModel):
    subject_code: str
    cycle_id: str
    g_type: str
    weight: float


class GroupTypeCreateResponse(BaseModel):
    id: str
    subject_code: str
    cycle_id: str
    g_type: str
    weight: float
    err: Optional[str] = None


class GroupCreateRequest(BaseModel):
    weekday: int
    g_type: str
    number: int
    pnp: str
    capacity: int
    start_time: time
    end_time: time
    subject_code: str
    cycle_id: str
    room_id: str


class GroupCreateResponse(BaseModel):
    id: str
    weekday: int
    g_type: str
    number: int
    pnp: str
    capacity: int
    start_time: time
    end_time: time
    subject_code: str
    cycle_id: str
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
    start_time: time
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
    subject_code: str = ""
    course_name: str
    g_type: str
    academic_cycle: str
    group_num: int
    weekday: Optional[int] = None
    pnp: str = ""
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    room: str = ""
    building: str
    nearest_classes: List[ClassOccurrence]
    filled: int
    capacity: int
    teachers: List[TeacherNameRef]
