from fastapi import APIRouter, Depends, HTTPException
from neo4j import AsyncSession

from app.database import get_session
from app.graph_backend.auth import Caller, require
from app.graph_backend.query import one, run
from app.schemas.student import (
    SetGroupGradeRequest,
    SetGroupGradeResponse,
    StudentDetailRequest,
    StudentDetailResponse,
    StudentInGroup,
    StudentsInGroupRequest,
    StudentsInGroupResponse,
)

router = APIRouter(tags=["teacher"])
_staff = require("Teacher", "Admin")

_STUDENT = """
MATCH (st:Student {idx: $student_idx})
OPTIONAL MATCH (st)-[:ENROLLED]->(ct:CurriculumTerm)
OPTIONAL CALL (st) {
  MATCH (st)-[:REGISTERED_IN]->(:Group)-[:OF_TYPE]->(:GroupType)<-[:HAS_TYPE]-(su:Subject)
  WITH DISTINCT st, su
  MATCH (su)-[:HAS_TYPE]->(gt:GroupType)
  OPTIONAL MATCH (st)-[rg:REGISTERED_IN]->(:Group)-[:OF_TYPE]->(gt)
  WHERE rg.grade IS NOT NULL
  WITH su, gt, avg(rg.grade) AS type_grade
  WITH su, collect({weight: gt.weight, grade: type_grade}) AS parts
  WHERE size(parts) > 0 AND all(part IN parts WHERE part.grade IS NOT NULL)
  WITH su.ects AS ects,
    reduce(total = 0.0, part IN parts | total + part.grade * part.weight)
      / reduce(total = 0.0, part IN parts | total + part.weight) AS subject_grade
  WITH sum(subject_grade * ects) AS weighted, sum(ects) AS ects_total
  RETURN CASE WHEN ects_total = 0 THEN null ELSE weighted / ects_total END AS avg_grade
}
RETURN
  st.idx AS idx,
  st.name AS name,
  st.surname AS surname,
  st.phone AS phone,
  st.photo AS photo,
  st.joined AS joined,
  avg_grade,
  collect(DISTINCT ct.id) AS term_ids
"""


@router.post("/students/detail", response_model=StudentDetailResponse)
async def student_detail(
    body: StudentDetailRequest,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_staff),
) -> StudentDetailResponse:
    if "Teacher" in caller.roles and "Admin" not in caller.roles:
        allowed = await one(
            session,
            """
            MATCH (t:Teacher {idx: $teacher_idx})-[:TEACHES]->(:Group)<-[:REGISTERED_IN]-(st:Student {idx: $student_idx})
            RETURN st.idx AS idx
            """,
            teacher_idx=caller.idx,
            student_idx=body.student_idx,
        )
        if allowed is None:
            raise HTTPException(status_code=403, detail="Forbidden")
    row = await one(session, _STUDENT, student_idx=body.student_idx)
    if row is None:
        return StudentDetailResponse(
            idx=body.student_idx,
            name="",
            surname="",
            phone="",
            joined="1970-01-01T00:00:00+00:00",
            err="Student not found",
        )
    row["term_ids"] = [item for item in row["term_ids"] if item is not None]
    return StudentDetailResponse(**row)


@router.post("/groups/students", response_model=StudentsInGroupResponse)
async def students_in_group(
    body: StudentsInGroupRequest,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_staff),
) -> StudentsInGroupResponse:
    if "Teacher" in caller.roles and "Admin" not in caller.roles:
        allowed = await one(
            session,
            """
            MATCH (t:Teacher {idx: $teacher_idx})-[:TEACHES]->(g:Group {id: $group_id})
            RETURN g.id AS id
            """,
            teacher_idx=caller.idx,
            group_id=body.group_id,
        )
        if allowed is None:
            raise HTTPException(status_code=403, detail="Forbidden")
    rows = await run(
        session,
        """
        MATCH (g:Group {id: $group_id})
        MATCH (st:Student)-[r:REGISTERED_IN]->(g)
        RETURN
          st.idx AS idx,
          st.name AS name,
          st.surname AS surname,
          st.phone AS phone,
          st.photo AS photo,
          st.joined AS joined,
          r.grade AS grade
        ORDER BY st.surname, st.name
        """,
        group_id=body.group_id,
    )
    return StudentsInGroupResponse(students=[StudentInGroup(**row) for row in rows])


@router.post("/groups/students/grade", response_model=SetGroupGradeResponse)
async def set_group_grade(
    body: SetGroupGradeRequest,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_staff),
) -> SetGroupGradeResponse:
    if "Teacher" in caller.roles and "Admin" not in caller.roles:
        allowed = await one(
            session,
            """
            MATCH (t:Teacher {idx: $teacher_idx})-[:TEACHES]->(g:Group {id: $group_id})
            RETURN g.id AS id
            """,
            teacher_idx=caller.idx,
            group_id=body.group_id,
        )
        if allowed is None:
            raise HTTPException(status_code=403, detail="Forbidden")
    row = await one(
        session,
        """
        MATCH (st:Student {idx: $student_idx})-[r:REGISTERED_IN]->(g:Group {id: $group_id})
        SET r.grade = $grade
        RETURN g.id AS group_id, st.idx AS student_idx, r.grade AS grade
        """,
        student_idx=body.student_idx,
        group_id=body.group_id,
        grade=body.grade,
    )
    if row is None:
        return SetGroupGradeResponse(
            group_id=body.group_id,
            student_idx=body.student_idx,
            grade=body.grade,
            err="Student is not registered in this group",
        )
    return SetGroupGradeResponse(**row)
