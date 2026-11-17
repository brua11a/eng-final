from fastapi import APIRouter, Depends
from neo4j import AsyncSession

from app.graph_backend.database import get_session
from app.graph_backend.auth import Caller, require
from app.graph_backend.errors import forbidden, not_found
from app.graph_backend.grades import average_grade
from app.graph_backend.query import one, run
from app.schemas.student import (
    SetGroupGradeRequest,
    SetGroupGradeResponse,
    StudentDetailResponse,
    StudentInGroup,
    StudentsInGroupResponse,
)
from app.graph_backend.teaching import teacher_groups
from app.schemas.teacher import MyTeachingGroupsResponse

router = APIRouter(tags=["teacher"])
_staff = require("Teacher", "Admin")
_teacher = require("Teacher")

_STUDENT = """
MATCH (st:Student {idx: $student_idx})
RETURN
  st.idx AS idx,
  st.name AS name,
  st.surname AS surname,
  st.phone AS phone,
  st.photo AS photo,
  st.joined AS joined,
  COLLECT { MATCH (st)-[:ENROLLED]->(ct:CurriculumTerm) RETURN ct.id } AS term_ids
"""

_STUDENT_GRADES = """
MATCH (st:Student {idx: $student_idx})-[:REGISTERED_IN]->(:Group)-[:OF_TYPE]->(:GroupType)<-[:HAS_TYPE]-(si:SubjectInstance)
WITH DISTINCT st, si
MATCH (si)-[:INSTANCE_OF]->(su:Subject)
MATCH (si)-[:OFFERED_IN]->(ac:AcademicCycle)
MATCH (si)-[:HAS_TYPE]->(gt:GroupType)
OPTIONAL MATCH (st)-[r:REGISTERED_IN]->(:Group)-[:OF_TYPE]->(gt)
RETURN
  su.code AS subject,
  su.ects AS ects,
  ac.year AS year,
  ac.season AS season,
  gt.id AS type,
  gt.weight AS weight,
  r.grade AS grade
"""


@router.get("/students/{student_idx}", response_model=StudentDetailResponse)
async def student_detail(
    student_idx: str,
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
            student_idx=student_idx,
        )
        if allowed is None:
            raise forbidden()
    row = await one(session, _STUDENT, student_idx=student_idx)
    if row is None:
        raise not_found("Student")
    grade_rows = await run(session, _STUDENT_GRADES, student_idx=student_idx)
    return StudentDetailResponse(**row, avg_grade=average_grade(grade_rows))


# The caller's own teaching groups. Another teacher's groups: GET /teachers/{idx}/groups.
@router.get("/me/groups", response_model=MyTeachingGroupsResponse)
async def my_teaching_groups(
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_teacher),
) -> MyTeachingGroupsResponse:
    return MyTeachingGroupsResponse(groups=await teacher_groups(session, caller.idx))


@router.get("/groups/{group_id}/students", response_model=StudentsInGroupResponse)
async def students_in_group(
    group_id: str,
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
            group_id=group_id,
        )
        if allowed is None:
            raise forbidden()
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
        group_id=group_id,
    )
    return StudentsInGroupResponse(students=[StudentInGroup(**row) for row in rows])


@router.put("/groups/{group_id}/students/{student_idx}/grade", response_model=SetGroupGradeResponse)
async def set_group_grade(
    group_id: str,
    student_idx: str,
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
            group_id=group_id,
        )
        if allowed is None:
            raise forbidden()
    row = await one(
        session,
        """
        MATCH (st:Student {idx: $student_idx})-[r:REGISTERED_IN]->(g:Group {id: $group_id})
        SET r.grade = $grade
        RETURN g.id AS group_id, st.idx AS student_idx, r.grade AS grade
        """,
        student_idx=student_idx,
        group_id=group_id,
        grade=body.grade,
    )
    if row is None:
        raise not_found("Student registered in this group")
    return SetGroupGradeResponse(**row)
