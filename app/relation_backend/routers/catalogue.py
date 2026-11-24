from fastapi import APIRouter, Depends
from psycopg import AsyncConnection

from app.graph_backend.auth import Caller, require
from app.graph_backend.cycles import cycle_sort_key
from app.graph_backend.errors import invalid
from app.graph_backend.routers.catalogue import _cycle_column, _faculty_label
from app.relation_backend.database import get_conn
from app.relation_backend.query import run
from app.schemas.opinion import OpinionItem, OpinionListResponse
from app.schemas.subject import SubjectCatalogueItem, SubjectCatalogueResponse

router = APIRouter(tags=["relational: catalogue"])
_logged_in = require("Student", "Teacher", "Admin")

# Strings are compared and sorted by code point (COLLATE "C"), like in Neo4j,
# so both backends return rows in the same order.

ACADEMIC_CYCLES = "SELECT id, year, season FROM academic_cycle"

# Counterpart of graph_backend/routers/catalogue.py::_SUBJECTS.
# One row per subject; `cycles` holds one cell per id in %(cycle_ids)s, in the same order.
SUBJECTS = """
SELECT
  su.code,
  su.name,
  se.ects,
  ARRAY(
    SELECT DISTINCT fa.name
    FROM term_subject ts
    JOIN curriculum_term ct ON ct.id = ts.term_id
    JOIN curriculum c ON c.id = ct.curriculum_id
    JOIN programme p ON p.id = c.programme_id
    JOIN faculty fa ON fa.id = p.faculty_id
    WHERE ts.subject_code = su.code
  ) AS faculties,
  ARRAY(
    SELECT json_build_object(
      'offered', EXISTS (
        SELECT 1
        FROM term_subject ts
        JOIN taught_in ti ON ti.term_id = ts.term_id
        WHERE ts.subject_code = su.code AND ti.cycle_id = cyc.id
      ),
      'group_count', (
        SELECT count(*)
        FROM group_type gt
        JOIN class_group g ON g.group_type_id = gt.id
        WHERE gt.subject_code = su.code AND gt.cycle_id = cyc.id
      ),
      -- A registration has no dates of its own: its period runs from the start of its first
      -- turn to the end of its last one.
      'registration_open', EXISTS (
        SELECT 1
        FROM group_type gt
        JOIN class_group g ON g.group_type_id = gt.id
        JOIN opens o ON o.group_id = g.id
        JOIN registration_turn rt ON rt.registration_id = o.registration_id
        WHERE gt.subject_code = su.code AND gt.cycle_id = cyc.id
        GROUP BY o.registration_id
        HAVING min((rt.date + rt.start_time) AT TIME ZONE 'Europe/Warsaw') <= now()
           AND now() < max((rt.date + rt.end_time) AT TIME ZONE 'Europe/Warsaw')
      )
    )
    FROM unnest(%(cycle_ids)s::text[]) WITH ORDINALITY AS cyc (id, ord)
    ORDER BY cyc.ord
  ) AS cycles
FROM subject su
LEFT JOIN subject_ects se ON se.subject_code = su.code
WHERE (%(name)s::text IS NULL OR strpos(lower(su.name), lower(%(name)s)) > 0)
  AND (%(code)s::text IS NULL OR strpos(lower(su.code), lower(%(code)s)) > 0)
ORDER BY su.name COLLATE "C"
"""

# Counterpart of graph_backend/routers/catalogue.py::_OPINIONS.
# Opinions are anonymous: opinion.student_idx is never read.
OPINIONS = """
SELECT
  o.id,
  o.grade::float8 AS grade,
  oc.content,
  -- Only the day: with the exact time a teacher could match an opinion to a student of a small group.
  (o.submit AT TIME ZONE 'Europe/Warsaw')::date AS submit,
  g.id AS group_id,
  su.code AS course_code,
  su.name AS course_name,
  gt.g_type,
  ac.year || ' ' || ac.season AS cycle,
  tp.idx AS teacher_idx,
  tp.name || ' ' || tp.surname AS teacher
FROM opinion o
LEFT JOIN opinion_content oc ON oc.opinion_id = o.id
JOIN class_group g ON g.id = o.group_id
JOIN person tp ON tp.idx = o.teacher_idx
JOIN group_type gt ON gt.id = g.group_type_id
JOIN subject su ON su.code = gt.subject_code
JOIN academic_cycle ac ON ac.id = gt.cycle_id
WHERE (%(teacher_idx)s::text IS NULL OR o.teacher_idx = %(teacher_idx)s)
  AND (%(group_id)s::text IS NULL OR o.group_id = %(group_id)s)
ORDER BY o.submit DESC
"""


@router.get("/subjects", response_model=SubjectCatalogueResponse)
async def subject_catalogue(
    name: str | None = None,
    code: str | None = None,
    conn: AsyncConnection = Depends(get_conn),
    caller: Caller = Depends(_logged_in),
) -> SubjectCatalogueResponse:
    cycle_rows = sorted(await run(conn, ACADEMIC_CYCLES), key=lambda r: cycle_sort_key(r["year"], r["season"]))
    rows = await run(conn, SUBJECTS, name=name, code=code, cycle_ids=[r["id"] for r in cycle_rows])
    for row in rows:
        row["faculty"] = _faculty_label(row.pop("faculties"))
    return SubjectCatalogueResponse(
        cycle_columns=[_cycle_column(r["year"], r["season"]) for r in cycle_rows],
        subjects=[SubjectCatalogueItem(**row) for row in rows],
    )


@router.get("/opinions", response_model=OpinionListResponse)
async def list_opinions(
    teacher_idx: str | None = None,
    group_id: str | None = None,
    conn: AsyncConnection = Depends(get_conn),
    caller: Caller = Depends(_logged_in),
) -> OpinionListResponse:
    if not teacher_idx and not group_id:
        raise invalid("teacher_idx or group_id is required")
    rows = await run(conn, OPINIONS, teacher_idx=teacher_idx, group_id=group_id)
    opinions = [OpinionItem(**row) for row in rows]
    avg = sum(o.grade for o in opinions) / len(opinions) if opinions else None
    return OpinionListResponse(opinions=opinions, avg_grade=avg)
