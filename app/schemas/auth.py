from datetime import date, datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, field_validator

# bcrypt only accepts passwords of up to 72 bytes.
MAX_PASSWORD_BYTES = 72

UserType = Literal["Teacher", "Student", "Admin"]


class AssignUserRequest(BaseModel):
    email: str
    passwd: str
    idx: str

    @field_validator("passwd")
    @classmethod
    def passwd_fits_bcrypt(cls, value: str) -> str:
        if len(value.encode()) > MAX_PASSWORD_BYTES:
            raise ValueError(f"password cannot be longer than {MAX_PASSWORD_BYTES} bytes")
        return value


class AssignUserResponse(BaseModel):
    email: str
    idx: str
    roles: List[UserType] = []


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    email: str
    idx: Optional[str] = None
    roles: List[UserType]
    token: str


# Extra properties the role needs: degree and working_since for Teacher, joined for Student.
class AddRoleRequest(BaseModel):
    degree: Optional[str] = None
    working_since: Optional[date] = None
    joined: Optional[datetime] = None


class RolesResponse(BaseModel):
    idx: str
    email: Optional[str] = None
    roles: List[UserType] = []


class UserUpdateRequest(BaseModel):
    active: bool


class UserAccountResponse(BaseModel):
    idx: str
    active: bool