from datetime import date, time
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

from .generic import OkResponse

RegType = Literal["zapisowa"]


class RegistrationItem(BaseModel):
    id: str
    name: str
    reg_type: RegType
    curriculum_id: str
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
    registration_id: str


class ShowCoursesInRegistrationResponse(BaseModel):
    courses: List[CourseInRegistration]


class RegisterToGroupRequest(BaseModel):
    subject_code: str
    group_id: str


class RegisterToGroupResponse(OkResponse):
    pass


class DeregisterFromGroupRequest(BaseModel):
    subject_code: str
    group_id: str


class DeregisterFromGroupResponse(OkResponse):
    pass


class OpenGroupsRequest(BaseModel):
    registration_id: str
    subject_code: str


class OpenGroup(BaseModel):
    id: str
    g_type: str
    number: int
    weekday: int
    start: time
    end: time
    capacity: int
    filled: int
    room: Optional[str] = None
    teacher: Optional[str] = None
    registered: bool


class OpenGroupsResponse(BaseModel):
    groups: List[OpenGroup]


class Enrolment(BaseModel):
    programme_id: str
    programme: str
    curriculum_id: str
    intake_year: str
    term_id: str
    sem: int
    cycle_id: Optional[str] = None
    year: Optional[str] = None
    season: Optional[str] = None


class MyEnrolmentsResponse(BaseModel):
    enrolments: List[Enrolment]


class RegistrationTurnInput(BaseModel):
    turn_number: int
    date: date
    start: time
    end: time


class StartRegistrationsRequest(BaseModel):
    name: str
    cycle_id: str
    faculty_id: str
    reg_type: RegType
    turns: List[RegistrationTurnInput]
    group_ids: List[str]


class StartRegistrationsResponse(BaseModel):
    id: str | None = None
    name: str | None = None
    reg_type: RegType | None = None
    turns: List[RegistrationTurnInput] = Field(default_factory=list)
    group_ids: List[str] = Field(default_factory=list)
    err: str | None = None
