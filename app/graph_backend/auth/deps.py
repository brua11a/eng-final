import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

Role = Literal["Student", "Teacher", "Admin"]
_bearer = HTTPBearer(auto_error=False)
_secret = os.getenv("JWT_SECRET", "dev-secret")
_algorithm = "HS256"


@dataclass
class Caller:
    email: str
    idx: str | None
    role: Role


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
        "role": caller.role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=12),
    }
    return jwt.encode(payload, _secret, algorithm=_algorithm)


async def get_caller(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Caller:
    if creds is None:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = jwt.decode(creds.credentials, _secret, algorithms=[_algorithm])
        role = payload["role"]
        if role not in ("Student", "Teacher", "Admin"):
            raise HTTPException(status_code=401, detail="Invalid token")
        return Caller(email=payload["sub"], idx=payload.get("idx"), role=role)
    except (JWTError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid token") from None


def require(*roles: Role):
    async def checker(caller: Caller = Depends(get_caller)) -> Caller:
        if caller.role not in roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return caller

    return checker
