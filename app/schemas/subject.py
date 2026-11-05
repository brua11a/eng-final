from typing import List, Optional
from pydantic import BaseModel

from .generic import TeacherNameRef
from .group import GroupTracked
from .subject_instance import SubjectInstanceItem


class SubjectCreateRequest(BaseModel):
    code: str
    name: str
    ects: Optional[int] = None


class SubjectCreateResponse(BaseModel):
    code: str
    name: str
    ects: Optional[int] = None
    err: Optional[str] = None


class SubjectCycleCell(BaseModel):
    instance_id: Optional[str] = None
    group_count: int = 0
    registration_open: bool = False


class SubjectCatalogueItem(BaseModel):
    code: str
    name: str
    ects: Optional[int] = None
    faculty: str = ""
    catalogue_code: str = ""
    cycles: List[SubjectCycleCell]


class SubjectCatalogueResponse(BaseModel):
    cycle_columns: List[str]
    subjects: List[SubjectCatalogueItem]


class SubjectDetailRequest(BaseModel):
    code: str


class SubjectDetailResponse(BaseModel):
    code: str
    name: str
    ects: Optional[int] = None
    taught_by: List[TeacherNameRef]
    instances: List[SubjectInstanceItem]


class SubjectGroupsRequest(BaseModel):
    instance_id: str


class SubjectGroupsResponse(BaseModel):
    name: str
    instance_id: str
    cycle: str
    groups: List[GroupTracked]
