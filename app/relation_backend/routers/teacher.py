from fastapi import APIRouter, Depends
from psycopg import AsyncConnection

from app.graph_backend.auth import Caller, require
from app.graph_backend.errors import forbidden, not_found
from app.graph_backend.grades import average_grade
from app.relation_backend.database import get_conn
from app.relation_backend.query import one, run
from app.schemas.student import (
    SetGroupGradeRequest,
    SetGroupGradeResponse,
    StudentDetailResponse,
    StudentInGroup,
    StudentsInGroupResponse,
)

router = APIRouter(tags=["relational: teacher"])
_staff = require("Teacher", "Admin")

# ReBAC checks: the same paths as in the graph, as joins of the join tables.
TEACHES_STUDENT = """
SELECT ri.student_idx AS idx
FROM teaches te
JOIN registered_in ri ON ri.group_id = te.group_id
WHERE te.teacher_idx = %(teacher_idx)s AND ri.student_idx = %(student_idx)s
LIMIT 1
"""

TEACHES_GROUP = """
SELECT group_id AS id FROM teaches
WHERE teacher_idx = %(teacher_idx)s AND group_id = %(group_id)s
"""

STUDENT = """
SELECT
  p.idx,
  p.name,
  p.surname,
  p.phone,
  ph.photo,
  s.joined,
  ARRAY(SELECT e.term_id FROM enrolled e WHERE e.student_idx = s.idx) AS term_ids
FROM student s
JOIN person p ON p.idx = s.idx
LEFT JOIN person_photo ph ON ph.idx = p.idx
WHERE s.idx = %(student_idx)s
"""

# Counterpart of graph_backend/routers/teacher.py::_STUDENT_GRADES: every group type of every
# subject instance the student attended, with the student's grade in a group of that type.
STUDENT_GRADES = """
SELECT
  su.code AS subject,
  se.ects,
  ac.year,
  ac.season,
  gt.id AS type,
  gt.weight,
  mine.grade::float8 AS grade
FROM (
  SELECT DISTINCT gt0.subject_code, gt0.cycle_id
  FROM registered_in ri
  JOIN class_group g ON g.id = ri.group_id
  JOIN group_type gt0 ON gt0.id = g.group_type_id
  WHERE ri.student_idx = %(student_idx)s
) si
JOIN subject su ON su.code = si.subject_code
LEFT JOIN subject_ects se ON se.subject_code = su.code
JOIN academic_cycle ac ON ac.id = si.cycle_id
JOIN group_type gt ON gt.subject_code = si.subject_code AND gt.cycle_id = si.cycle_id
LEFT JOIN (
  SELECT gr.grade, g.group_type_id
  FROM grade gr
  JOIN class_group g ON g.id = gr.group_id
  WHERE gr.student_idx = %(student_idx)s
) mine ON mine.group_type_id = gt.id
"""

STUDENTS_IN_GROUP = """
SELECT
  p.idx,
  p.name,
  p.surname,
  p.phone,
  ph.photo,
  s.joined,
  gr.grade::float8 AS grade
FROM registered_in ri
JOIN student s ON s.idx = ri.student_idx
JOIN person p ON p.idx = s.idx
LEFT JOIN person_photo ph ON ph.idx = p.idx
LEFT JOIN grade gr ON gr.student_idx = ri.student_idx AND gr.group_id = ri.group_id
WHERE ri.group_id = %(group_id)s
ORDER BY p.surname COLLATE "C", p.name COLLATE "C"
"""

# The grade has its own table, so setting it is an upsert. The row is taken from registered_in:
# when the student is not registered in the group nothing is inserted and nothing is returned (404).
SET_GRADE = """
INSERT INTO grade (student_idx, group_id, grade)
SELECT student_idx, group_id, %(grade)s
FROM registered_in
WHERE student_idx = %(student_idx)s AND group_id = %(group_id)s
ON CONFLICT (student_idx, group_id) DO UPDATE SET grade = excluded.grade
RETURNING group_id, student_idx, grade::float8 AS grade
"""


def _teacher_only(caller: Caller) -> bool:
    return "Teacher" in caller.roles and "Admin" not in caller.roles


@router.get("/students/{student_idx}", response_model=StudentDetailResponse)
async def student_detail(
    student_idx: str,
    conn: AsyncConnection = Depends(get_conn),
    caller: Caller = Depends(_staff),
) -> StudentDetailResponse:
    if _teacher_only(caller):
        if await one(conn, TEACHES_STUDENT, teacher_idx=caller.idx, student_idx=student_idx) is None:
            raise forbidden()
    row = await one(conn, STUDENT, student_idx=student_idx)
    if row is None:
        raise not_found("Student")
    grade_rows = await run(conn, STUDENT_GRADES, student_idx=student_idx)
    return StudentDetailResponse(**row, avg_grade=average_grade(grade_rows))


@router.get("/groups/{group_id}/students", response_model=StudentsInGroupResponse)
async def students_in_group(
    group_id: str,
    conn: AsyncConnection = Depends(get_conn),
    caller: Caller = Depends(_staff),
) -> StudentsInGroupResponse:
    if _teacher_only(caller):
        if await one(conn, TEACHES_GROUP, teacher_idx=caller.idx, group_id=group_id) is None:
            raise forbidden()
    rows = await run(conn, STUDENTS_IN_GROUP, group_id=group_id)
    return StudentsInGroupResponse(students=[StudentInGroup(**row) for row in rows])


@router.put("/groups/{group_id}/students/{student_idx}/grade", response_model=SetGroupGradeResponse)
async def set_group_grade(
    group_id: str,
    student_idx: str,
    body: SetGroupGradeRequest,
    conn: AsyncConnection = Depends(get_conn),
    caller: Caller = Depends(_staff),
) -> SetGroupGradeResponse:
    if _teacher_only(caller):
        if await one(conn, TEACHES_GROUP, teacher_idx=caller.idx, group_id=group_id) is None:
            raise forbidden()
    row = await one(conn, SET_GRADE, student_idx=student_idx, group_id=group_id, grade=body.grade)
    if row is None:
        raise not_found("Student registered in this group")
    return SetGroupGradeResponse(**row)
