from datetime import date, time
from typing import List, Literal, Optional
from pydantic import BaseModel


RegType = Literal["zapisowa"]


class RegistrationItem(BaseModel):
    id: str
    name: str
    reg_type: RegType
    curriculum_id: Optional[str] = None
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


class ShowCoursesInRegistrationResponse(BaseModel):
    courses: List[CourseInRegistration]


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
    id: str
    name: str
    reg_type: RegType
    turns: List[RegistrationTurnInput]
    group_ids: List[str]
