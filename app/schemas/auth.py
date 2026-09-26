from typing import Literal, Optional
from pydantic import BaseModel

from .generic import OkResponse

UserType = Literal["Teacher", "Student"]


class AssignUserRequest(BaseModel):
    email: str
    passwd: str
    user_type: UserType
    assigned_id: str


class AssignUserResponse(BaseModel):
    email: str
    owner_type: UserType
    owner_idx: str
    err: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(OkResponse):
    pass