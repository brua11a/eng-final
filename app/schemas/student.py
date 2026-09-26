from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class StudentCreateRequest(BaseModel):
    name: str
    surname: str
    phone: Optional[str] = None
    photo: Optional[str] = None
    joined: datetime


class StudentCreateResponse(BaseModel):
    idx: str
    name: str
    surname: str
    phone: Optional[str] = None
    photo: Optional[str] = None
    joined: datetime
    err: Optional[str] = None


class StudentDetailRequest(BaseModel):
    student_idx: str


class StudentDetailResponse(BaseModel):
    idx: str
    name: str
    surname: str
    phone: Optional[str] = None
    photo: Optional[str] = None
    joined: datetime
    err: Optional[str] = None


class StudentInGroup(BaseModel):
    idx: str
    name: str
    surname: str
    phone: Optional[str] = None
    photo: Optional[str] = None
    joined: datetime


class StudentsInGroupRequest(BaseModel):
    group_id: int


class StudentsInGroupResponse(BaseModel):
    students: List[StudentInGroup]