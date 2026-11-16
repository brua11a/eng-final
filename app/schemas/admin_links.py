from typing import List

from pydantic import BaseModel, Field


class ProgrammeCreateRequest(BaseModel):
    name: str
    faculty_id: str


class ProgrammeCreateResponse(BaseModel):
    id: str
    name: str
    faculty_id: str


class AdminCreateRequest(BaseModel):
    idx: str = Field(pattern=r"^A[0-9]+$")
    name: str
    surname: str
    phone: str


class AdminCreateResponse(BaseModel):
    idx: str
    name: str
    surname: str
    phone: str


class TermSubjectRequest(BaseModel):
    term_id: str
    subject_code: str


class TermSubjectResponse(BaseModel):
    term_id: str
    subject_code: str


class EnrolStudentRequest(BaseModel):
    term_id: str


class EnrolStudentResponse(BaseModel):
    student_idx: str
    term_id: str


class AssignTurnRequest(BaseModel):
    turn_id: str
    student_idxs: List[str]


class AssignTurnResponse(BaseModel):
    turn_id: str
    assigned: List[str] = []


class DeanRegisterRequest(BaseModel):
    student_idx: str
    group_id: str
    ignore_capacity: bool = False


class DeanRegisterResponse(BaseModel):
    student_idx: str
    group_id: str
    ignore_capacity: bool = False


class NextIdxResponse(BaseModel):
    teacher: str
    student: str
    admin: str
