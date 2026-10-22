from fastapi import APIRouter, Depends, HTTPException
from neo4j import AsyncSession

from app.database import get_session
from app.graph_backend.auth import Caller, require
from app.graph_backend.query import one, run
from app.schemas.student import (
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
RETURN
  st.idx AS idx,
  st.name AS name,
  st.surname AS surname,
  st.phone AS phone,
  st.photo AS photo,
  st.joined AS joined,
  st.avg_grade AS avg_grade,
  collect(DISTINCT ct.id) AS term_ids
"""


@router.post("/students/detail", response_model=StudentDetailResponse)
async def student_detail(
    body: StudentDetailRequest,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_staff),
) -> StudentDetailResponse:
    if caller.role == "Teacher":
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
    if caller.role == "Teacher":
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
        MATCH (st:Student)-[:REGISTERED_IN]->(g)
        RETURN
          st.idx AS idx,
          st.name AS name,
          st.surname AS surname,
          st.phone AS phone,
          st.photo AS photo,
          st.joined AS joined
        ORDER BY st.surname, st.name
        """,
        group_id=body.group_id,
    )
    return StudentsInGroupResponse(students=[StudentInGroup(**row) for row in rows])
