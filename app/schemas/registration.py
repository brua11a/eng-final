from datetime import date, time
from typing import List, Literal
from pydantic import BaseModel, Field

from .generic import OkResponse

RegType = Literal["zapisowa"]


class RegistrationItem(BaseModel):
    id: int
    name: str
    reg_type: RegType
    curriculum_id: int
    turn_number: int
    date: date
    start: time
    end: time


class ShowRegistrationsResponse(BaseModel):
    available_registrations: List[RegistrationItem]


class ClassInfo(BaseModel):
    g_type: str
    count: int


class CourseInRegistration(BaseModel):
    id: str
    name: str
    classes: List[ClassInfo]
    academic_cycle: str


class ShowCoursesInRegistrationRequest(BaseModel):
    registration_id: int


class ShowCoursesInRegistrationResponse(BaseModel):
    courses: List[CourseInRegistration]


class RegisterToGroupRequest(BaseModel):
    course_id: str
    group_id: int


class RegisterToGroupResponse(OkResponse):
    pass


class RegistrationTurnInput(BaseModel):
    turn_number: int
    date: date
    start: time
    end: time


class StartRegistrationsRequest(BaseModel):
    name: str
    cycle_id: int
    faculty_id: int
    reg_type: RegType
    turns: List[RegistrationTurnInput]
    group_ids: List[int]


class StartRegistrationsResponse(BaseModel):
    id: int | None = None
    name: str | None = None
    reg_type: RegType | None = None
    turns: List[RegistrationTurnInput] = Field(default_factory=list)
    group_ids: List[int] = Field(default_factory=list)
    err: str | None = None
