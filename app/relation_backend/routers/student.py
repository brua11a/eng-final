from fastapi import APIRouter, Depends
from psycopg import AsyncConnection

from app.graph_backend.auth import Caller, require
from app.graph_backend.errors import conflict, forbidden
from app.relation_backend.database import get_conn
from app.relation_backend.query import one, run
from app.schemas.registration import OpenGroup, OpenGroupsResponse

router = APIRouter(tags=["relational: student"])
_student = require("Student")

# Counterpart of _CAN_USE_REGISTRATION. `assigned` stores the registration next to the turn
# (needed for the "one turn per registration" constraint), so no join is required.
CAN_USE_REGISTRATION = """
SELECT registration_id AS id
FROM assigned
WHERE student_idx = %(student_idx)s AND registration_id = %(registration_id)s
"""

# Counterpart of the query in graph_backend/routers/student.py::show_groups.
OPEN_GROUPS = """
SELECT
  g.id,
  gt.g_type,
  g.number,
  g.weekday,
  g.start_time AS start,
  g.end_time AS "end",
  g.capacity,
  (SELECT count(*) FROM registered_in ri WHERE ri.group_id = g.id) AS filled,
  r.building || ' ' || r.room_num AS room,
  tp.name || ' ' || tp.surname AS teacher,
  EXISTS (
    SELECT 1 FROM registered_in ri
    WHERE ri.group_id = g.id AND ri.student_idx = %(student_idx)s
  ) AS registered
FROM opens o
JOIN class_group g ON g.id = o.group_id
JOIN group_type gt ON gt.id = g.group_type_id
LEFT JOIN in_room ir ON ir.group_id = g.id
LEFT JOIN room r ON r.id = ir.room_id
LEFT JOIN teaches te ON te.group_id = g.id
LEFT JOIN person tp ON tp.idx = te.teacher_idx
WHERE o.registration_id = %(registration_id)s
  AND gt.subject_code = %(subject_code)s
ORDER BY gt.g_type COLLATE "C", g.number
"""

# Registration to a group (counterpart of graph_backend/routers/student.py::_REGISTER).
#
# PostgreSQL also runs at READ COMMITTED here, but a statement sees a snapshot taken when it
# started: after waiting for a row lock it re-reads only the locked row, not the other rows it
# counts. So, unlike the single Cypher query, the locks are taken by separate statements first,
# and the conditions are checked by a later statement, with a fresh snapshot.
# Locks are always taken in the same order (student, then group) to avoid deadlocks.
LOCK_STUDENT = "SELECT idx FROM student WHERE idx = %(student_idx)s FOR UPDATE"

# The group is returned (and locked) only when one of the student's turns that opens it is in
# progress - this is the ReBAC check (403 when no row).
LOCK_GROUP_IN_TURN = """
SELECT g.capacity, g.group_type_id
FROM class_group g
WHERE g.id = %(group_id)s
  AND EXISTS (
    SELECT 1
    FROM assigned a
    JOIN registration_turn rt ON rt.id = a.turn_id
    JOIN opens o ON o.registration_id = a.registration_id
    WHERE a.student_idx = %(student_idx)s
      AND o.group_id = g.id
      -- Turn hours are wall-clock time in the university's zone (see app/university_time.py).
      AND (rt.date + rt.start_time) AT TIME ZONE 'Europe/Warsaw' <= now()
      AND now() < (rt.date + rt.end_time) AT TIME ZONE 'Europe/Warsaw'
  )
FOR UPDATE OF g
"""

REGISTER = """
WITH checks AS (
  SELECT
    EXISTS (
      SELECT 1 FROM registered_in
      WHERE student_idx = %(student_idx)s AND group_id = %(group_id)s
    ) AS already,
    EXISTS (
      SELECT 1
      FROM registered_in ri
      JOIN class_group other ON other.id = ri.group_id
      WHERE ri.student_idx = %(student_idx)s
        AND other.group_type_id = %(group_type_id)s
        AND other.id <> %(group_id)s
    ) AS conflict,
    (SELECT count(*) FROM registered_in WHERE group_id = %(group_id)s) >= %(capacity)s AS is_full
),
decision AS (
  SELECT CASE
    WHEN already THEN 'ok'
    WHEN conflict THEN 'conflict'
    WHEN is_full THEN 'full'
    ELSE 'ok'
  END AS status
  FROM checks
),
inserted AS (
  INSERT INTO registered_in (student_idx, group_id)
  SELECT %(student_idx)s, %(group_id)s FROM decision WHERE status = 'ok'
  ON CONFLICT DO NOTHING
)
SELECT status FROM decision
"""


async def _require_registration(conn: AsyncConnection, student_idx: str, registration_id: str) -> None:
    if await one(conn, CAN_USE_REGISTRATION, student_idx=student_idx, registration_id=registration_id) is None:
        raise forbidden()


@router.get("/me/registrations/{registration_id}/groups", response_model=OpenGroupsResponse)
async def show_groups(
    registration_id: str,
    subject_code: str,
    conn: AsyncConnection = Depends(get_conn),
    caller: Caller = Depends(_student),
) -> OpenGroupsResponse:
    await _require_registration(conn, caller.idx, registration_id)
    rows = await run(
        conn, OPEN_GROUPS, student_idx=caller.idx, registration_id=registration_id, subject_code=subject_code
    )
    return OpenGroupsResponse(groups=[OpenGroup(**row) for row in rows])


@router.put("/me/registered-groups/{group_id}", status_code=204)
async def register_to_group(
    group_id: str,
    conn: AsyncConnection = Depends(get_conn),
    caller: Caller = Depends(_student),
) -> None:
    # All three statements run in the request's transaction (database.get_conn).
    await run(conn, LOCK_STUDENT, student_idx=caller.idx)
    group = await one(conn, LOCK_GROUP_IN_TURN, student_idx=caller.idx, group_id=group_id)
    if group is None:
        raise forbidden("Group not open to you, or outside your registration turn")
    row = await one(conn, REGISTER, student_idx=caller.idx, group_id=group_id, **group)
    if row["status"] == "conflict":
        raise conflict("You are already registered in another group of this type for this subject")
    if row["status"] == "full":
        raise conflict("Group is full")
