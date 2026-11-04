from datetime import date, datetime
from typing import List, Literal, Optional
from pydantic import BaseModel

from .generic import OkResponse

UserType = Literal["Teacher", "Student", "Admin"]


class AssignUserRequest(BaseModel):
    email: str
    passwd: str
    idx: str


class AssignUserResponse(BaseModel):
    email: str
    idx: str
    roles: List[UserType] = []
    err: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(OkResponse):
    email: Optional[str] = None
    idx: Optional[str] = None
    roles: List[UserType] = []
    token: Optional[str] = None


class AddRoleRequest(BaseModel):
    idx: str
    role: UserType
    degree: Optional[str] = None
    working_since: Optional[date] = None
    joined: Optional[datetime] = None


class AddRoleResponse(BaseModel):
    idx: str
    email: Optional[str] = None
    roles: List[UserType] = []
    err: Optional[str] = None


class UserIdxRequest(BaseModel):
    idx: str


class UserAccountResponse(BaseModel):
    idx: str
    err: Optional[str] = None