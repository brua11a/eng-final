from typing import List, Optional

from pydantic import BaseModel


class SubjectInstanceItem(BaseModel):
    id: str
    cycle: str
    catalogue_code: str = ""
    group_count: int = 0


class SubjectInstanceCreateRequest(BaseModel):
    subject_code: str
    cycle_id: str
    catalogue_code: str = ""


class SubjectInstanceCreateResponse(BaseModel):
    id: str
    subject_code: str
    cycle_id: str
    catalogue_code: str = ""
    err: Optional[str] = None
