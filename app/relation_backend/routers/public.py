from fastapi import APIRouter, Depends
from psycopg import AsyncConnection

from app.graph_backend.auth import DUMMY_PASSWORD_HASH, Caller, create_token, roles_from_flags, verify_password
from app.graph_backend.errors import forbidden, unauthorized
from app.relation_backend.database import get_conn
from app.relation_backend.query import one
from app.schemas.auth import LoginRequest, LoginResponse

router = APIRouter(tags=["relational: public"])

# Counterpart of graph_backend/routers/public.py::_LOGIN.
# Roles are separate tables, so each role is one LEFT JOIN instead of a label check.
LOGIN = """
SELECT
  u.passwd_hash,
  u.email,
  u.idx,
  u.deactivated_at IS NOT NULL AS inactive,
  a.idx IS NOT NULL AS admin,
  t.idx IS NOT NULL AS teacher,
  s.idx IS NOT NULL AS student
FROM app_user u
LEFT JOIN admin a ON a.idx = u.idx
LEFT JOIN teacher t ON t.idx = u.idx
LEFT JOIN student s ON s.idx = u.idx
WHERE u.email = %(email)s
"""


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, conn: AsyncConnection = Depends(get_conn)) -> LoginResponse:
    row = await one(conn, LOGIN, email=body.email)
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
    return LoginResponse(email=caller.email, idx=caller.idx, roles=list(caller.roles), token=create_token(caller))
