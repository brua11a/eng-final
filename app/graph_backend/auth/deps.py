import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

import bcrypt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

from app.graph_backend.errors import forbidden, unauthorized

Role = Literal["Student", "Teacher", "Admin"]
_bearer = HTTPBearer(auto_error=False)
_secret = os.environ["JWT_SECRET"]
_algorithm = "HS256"


def roles_from_flags(admin: bool, teacher: bool, student: bool) -> tuple[Role, ...]:
    found: list[Role] = []
    if admin:
        found.append("Admin")
    if teacher:
        found.append("Teacher")
    if student:
        found.append("Student")
    return tuple(found)


@dataclass
class Caller:
    email: str
    idx: str | None
    roles: tuple[Role, ...]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def create_token(caller: Caller) -> str:
    payload = {
        "sub": caller.email,
        "idx": caller.idx,
        "roles": list(caller.roles),
        "exp": datetime.now(timezone.utc) + timedelta(hours=12),
    }
    return jwt.encode(payload, _secret, algorithm=_algorithm)


async def get_caller(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Caller:
    if creds is None:
        raise unauthorized("Missing token")
    try:
        payload = jwt.decode(creds.credentials, _secret, algorithms=[_algorithm])
        raw = payload.get("roles")
        if raw is None and payload.get("role") in ("Student", "Teacher", "Admin"):
            raw = [payload["role"]]
        if not isinstance(raw, list) or any(role not in ("Student", "Teacher", "Admin") for role in raw):
            raise unauthorized("Invalid token")
        roles = tuple(role for role in ("Admin", "Teacher", "Student") if role in raw)
        if not roles:
            raise unauthorized("Invalid token")
        return Caller(email=payload["sub"], idx=payload.get("idx"), roles=roles)
    except (jwt.PyJWTError, KeyError):
        raise unauthorized("Invalid token") from None


def require(*roles: Role):
    async def checker(caller: Caller = Depends(get_caller)) -> Caller:
        if not any(role in caller.roles for role in roles):
            raise forbidden()
        return caller

    return checker
