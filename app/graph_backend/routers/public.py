from fastapi import APIRouter, Depends
from neo4j import AsyncSession

from app.graph_backend.database import get_session
from app.graph_backend.auth import DUMMY_PASSWORD_HASH, create_token, roles_from_flags, verify_password
from app.graph_backend.auth.deps import Caller
from app.graph_backend.errors import forbidden, unauthorized
from app.graph_backend.query import one
from app.schemas.auth import LoginRequest, LoginResponse

router = APIRouter(tags=["public"])

_LOGIN = """
MATCH (u:User {email: $email})
RETURN
  u.passwd_hash AS passwd_hash,
  u.email AS email,
  u.idx AS idx,
  u:Inactive AS inactive,
  u:Admin AS admin,
  u:Teacher AS teacher,
  u:Student AS student
"""


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)) -> LoginResponse:
    row = await one(session, _LOGIN, email=body.email)
    # bcrypt is always run, so a missing account takes as long as a wrong password.
    password_hash = row["passwd_hash"] if row is not None else DUMMY_PASSWORD_HASH
    password_ok = verify_password(body.password, password_hash)
    if row is None or not password_ok:
        raise unauthorized("Invalid email or password")
    if row["inactive"]:
        raise forbidden("Account inactive")
    roles = roles_from_flags(row["admin"], row["teacher"], row["student"])
    if not roles:
        raise forbidden("Account has no role")
    caller = Caller(email=row["email"], idx=row["idx"], roles=roles)
    return LoginResponse(
        email=caller.email,
        idx=caller.idx,
        roles=list(caller.roles),
        token=create_token(caller),
    )
