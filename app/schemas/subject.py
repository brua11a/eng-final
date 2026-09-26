from typing import List, Optional
from pydantic import BaseModel

from .generic import TeacherNameRef
from .group import GroupNested, GroupTracked


class SubjectCreateRequest(BaseModel):
    code: str
    name: str
    ects: Optional[int] = None


class SubjectCreateResponse(BaseModel):
    code: str
    name: str
    ects: Optional[int] = None
    err: Optional[str] = None


class SubjectAndGroups(BaseModel):
    code: str
    name: str
    ects: Optional[int] = None
    groups: List[GroupNested]


class SubjectCatalogueResponse(BaseModel):
    subject_and_groups: List[SubjectAndGroups]


class SubjectFindRequest(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None


class SubjectFindResponse(BaseModel):
    subject_and_groups: List[SubjectAndGroups]


class SubjectDetailRequest(BaseModel):
    code: str


class SubjectDetailResponse(BaseModel):
    name: str
    ects: Optional[int] = None
    coordinated: TeacherNameRef
    taught_by: List[TeacherNameRef]


class SubjectGroupsRequest(BaseModel):
    code: str


class SubjectGroupsResponse(BaseModel):
    name: str
    groups: List[GroupTracked]