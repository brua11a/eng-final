from fastapi import APIRouter, Depends
from neo4j import AsyncSession

from app.database import get_session
from app.graph_backend.auth import create_token, verify_password
from app.graph_backend.auth.deps import Caller
from app.graph_backend.query import one
from app.schemas.auth import LoginRequest, LoginResponse

router = APIRouter(tags=["public"])

_LOGIN = """
MATCH (u:User {email: $email})
RETURN
  u.passwd_hash AS passwd_hash,
  u.email AS email,
  u.idx AS idx,
  CASE
    WHEN u:Admin THEN 'Admin'
    WHEN u:Teacher THEN 'Teacher'
    WHEN u:Student THEN 'Student'
  END AS user_type
"""


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)) -> LoginResponse:
    row = await one(session, _LOGIN, email=body.email)
    if row is None or not verify_password(body.password, row["passwd_hash"]):
        return LoginResponse(ok=False, err="Invalid email or password")
    caller = Caller(email=row["email"], idx=row["idx"], role=row["user_type"])
    return LoginResponse(
        ok=True,
        email=caller.email,
        idx=caller.idx,
        user_type=caller.role,
        token=create_token(caller),
    )
