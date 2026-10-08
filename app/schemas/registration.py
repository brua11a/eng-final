from datetime import date, time
from typing import List, Literal
from pydantic import BaseModel, Field

from .generic import OkResponse

RegType = Literal["zapisowa", "poprawkowa"]


class RegistrationItem(BaseModel):
    id: int
    date: date
    start: time
    end: time
    reg_type: RegType


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
    cycle_id: int
    faculty_id: int
    reg_type: RegType
    turns: List[RegistrationTurnInput]


class StartRegistrationsResponse(BaseModel):
    registrations: List[RegistrationItem] = Field(default_factory=list)
    err: str | None = None
