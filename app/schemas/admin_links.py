from typing import List, Optional

from pydantic import BaseModel


class ProgrammeCreateRequest(BaseModel):
    name: str
    faculty_id: str


class ProgrammeCreateResponse(BaseModel):
    id: Optional[str] = None
    name: str
    faculty_id: str
    err: Optional[str] = None


class AdminCreateRequest(BaseModel):
    name: str
    surname: str
    phone: str


class AdminCreateResponse(BaseModel):
    idx: Optional[str] = None
    name: str
    surname: str
    phone: str
    err: Optional[str] = None


class TermSubjectRequest(BaseModel):
    term_id: str
    subject_code: str


class TermSubjectResponse(BaseModel):
    term_id: str
    subject_code: str
    err: Optional[str] = None


class EnrolStudentRequest(BaseModel):
    student_idx: str
    term_id: str


class EnrolStudentResponse(BaseModel):
    student_idx: str
    term_id: str
    err: Optional[str] = None


class AssignTurnRequest(BaseModel):
    turn_id: str
    student_idxs: List[str]


class AssignTurnResponse(BaseModel):
    turn_id: str
    assigned: List[str] = []
    err: Optional[str] = None


class DeanRegisterRequest(BaseModel):
    student_idx: str
    group_id: str
    ignore_capacity: bool = False


class DeanRegisterResponse(BaseModel):
    student_idx: str
    group_id: str
    ignore_capacity: bool = False
    err: Optional[str] = None
