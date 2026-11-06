from fastapi import APIRouter, Depends, HTTPException
from neo4j import AsyncSession

from app.database import get_session
from app.graph_backend.auth import Caller, require
from app.graph_backend.grades import average_grade
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
from app.graph_backend.teaching import teacher_groups
from app.schemas.teacher import MyTeachingGroupsResponse

router = APIRouter(tags=["teacher"])
_staff = require("Teacher", "Admin")


def _resolve_teacher_idx(caller: Caller, teacher_idx: str | None) -> str:
    if "Admin" in caller.roles and teacher_idx:
        return teacher_idx
    if "Teacher" in caller.roles and caller.idx:
        return caller.idx
    if "Admin" in caller.roles:
        raise HTTPException(status_code=400, detail="teacher_idx is required")
    raise HTTPException(status_code=403, detail="Forbidden")

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
MATCH (st:Student {idx: $student_idx})-[:REGISTERED_IN]->(attended:Group)-[:OF_TYPE]->(:GroupType)<-[:HAS_TYPE]-(su:Subject)
MATCH (attended)-[:IN_CYCLE]->(ac:AcademicCycle)
WITH DISTINCT st, su, ac
MATCH (su)-[:HAS_TYPE]->(gt:GroupType)
OPTIONAL MATCH (st)-[r:REGISTERED_IN]->(g:Group)-[:OF_TYPE]->(gt)
WHERE (g)-[:IN_CYCLE]->(ac)
RETURN
  su.code AS subject,
  su.ects AS ects,
  ac.year AS year,
  ac.season AS season,
  gt.id AS type,
  gt.weight AS weight,
  r.grade AS grade
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
    grade_rows = await run(session, _STUDENT_GRADES, student_idx=body.student_idx)
    return StudentDetailResponse(**row, avg_grade=average_grade(grade_rows))


@router.get("/me/groups", response_model=MyTeachingGroupsResponse)
async def my_teaching_groups(
    teacher_idx: str | None = None,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_staff),
) -> MyTeachingGroupsResponse:
    idx = _resolve_teacher_idx(caller, teacher_idx)
    return MyTeachingGroupsResponse(groups=await teacher_groups(session, idx))


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
