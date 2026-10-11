from typing import List
from pydantic import BaseModel


class GroupLite(BaseModel):
    g_type: str
    number: int


class GroupInList(BaseModel):
    cycle: str
    name: str
    course_code: str
    groups: List[GroupLite]


# TODO: actual dashboard