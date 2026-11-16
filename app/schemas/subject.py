from typing import List, Optional
from pydantic import BaseModel

from .generic import TeacherNameRef
from .group import GroupTracked


class SubjectUpsertRequest(BaseModel):
    name: str
    ects: Optional[int] = None


class SubjectCreateResponse(BaseModel):
    code: str
    name: str
    ects: Optional[int] = None


class SubjectCycleCell(BaseModel):
    offered: bool = False
    group_count: int = 0
    registration_open: bool = False


class SubjectCatalogueItem(BaseModel):
    code: str
    name: str
    ects: Optional[int] = None
    faculty: str = ""
    cycles: List[SubjectCycleCell]


class SubjectCatalogueResponse(BaseModel):
    cycle_columns: List[str]
    subjects: List[SubjectCatalogueItem]


class SubjectOfferingItem(BaseModel):
    cycle_id: str
    cycle: str
    group_count: int = 0


class SubjectDetailResponse(BaseModel):
    code: str
    name: str
    ects: Optional[int] = None
    taught_by: List[TeacherNameRef]
    offerings: List[SubjectOfferingItem]


class SubjectGroupsResponse(BaseModel):
    name: str
    subject_code: str
    cycle_id: str
    cycle: str
    groups: List[GroupTracked]
