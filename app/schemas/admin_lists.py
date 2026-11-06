from typing import List

from pydantic import BaseModel


class SubjectListItem(BaseModel):
    code: str
    name: str


class SubjectListResponse(BaseModel):
    subjects: List[SubjectListItem]


class AdminCurriculumItem(BaseModel):
    id: str
    programme_name: str
    intake_year: str


class AdminCurriculumListResponse(BaseModel):
    curricula: List[AdminCurriculumItem]


class AdminTeacherItem(BaseModel):
    idx: str
    name: str
    surname: str


class AdminTeacherListResponse(BaseModel):
    teachers: List[AdminTeacherItem]


class AdminGroupItem(BaseModel):
    id: str
    label: str


class AdminGroupListResponse(BaseModel):
    groups: List[AdminGroupItem]
