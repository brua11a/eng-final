from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from neo4j import AsyncSession

from app.database import get_session
from app.graph_backend.auth import Caller, require
from app.graph_backend.query import next_id, one, run
from app.schemas.academic_cycle import (
    MyAcademicCycleDetailRequest,
    MyAcademicCycleDetailResponse,
    MyAcademicCycleItem,
    MyAcademicCyclesResponse,
)
from app.schemas.dashboard import DashboardResponse, RegisteredGroup
from app.schemas.opinion import OpinionCreateRequest, OpinionCreateResponse
from app.schemas.registration import (
    ClassInfo,
    CourseInRegistration,
    Enrolment,
    MyEnrolmentsResponse,
    OpenGroup,
    OpenGroupsRequest,
    OpenGroupsResponse,
    RegisterToGroupRequest,
    RegisterToGroupResponse,
    RegistrationItem,
    ShowCoursesInRegistrationRequest,
    ShowCoursesInRegistrationResponse,
    ShowRegistrationsResponse,
)

router = APIRouter(tags=["student"])


def _zoned_datetime(value: datetime) -> str:
    text = value.isoformat()
    return text if value.tzinfo else f"{text}+01:00"


_student = require("Student")
_opinion_roles = require("Student", "Admin")

_CAN_USE_REGISTRATION = """
MATCH (st:Student {idx: $student_idx})-[:ASSIGNED]->(:TurnAssignment)-[:FOR_TURN]->(:RegistrationTurn)<-[:HAS_TURN]-(reg:Registration {id: $registration_id})
RETURN reg.id AS id
"""


async def _require_registration(session: AsyncSession, student_idx: str, registration_id: int) -> None:
    row = await one(
        session,
        _CAN_USE_REGISTRATION,
        student_idx=student_idx,
        registration_id=registration_id,
    )
    if row is None:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/me/registrations", response_model=ShowRegistrationsResponse)
async def show_registrations(
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_student),
) -> ShowRegistrationsResponse:
    rows = await run(
        session,
        """
        MATCH (st:Student {idx: $student_idx})-[:ASSIGNED]->(tu:TurnAssignment)-[:FOR_TURN]->(rt:RegistrationTurn)
        MATCH (tu)-[:FOR_CURRICULUM]->(c:Curriculum)
        MATCH (reg:Registration)-[:HAS_TURN]->(rt)
        RETURN
          reg.id AS id,
          reg.name AS name,
          reg.reg_type AS reg_type,
          c.id AS curriculum_id,
          rt.turn_number AS turn_number,
          rt.date AS date,
          rt.start_hr AS start,
          rt.end_time AS end
        """,
        student_idx=caller.idx,
    )
    return ShowRegistrationsResponse(
        available_registrations=[RegistrationItem(**row) for row in rows]
    )


@router.post("/me/registrations/courses", response_model=ShowCoursesInRegistrationResponse)
async def show_courses(
    body: ShowCoursesInRegistrationRequest,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_student),
) -> ShowCoursesInRegistrationResponse:
    await _require_registration(session, caller.idx, body.registration_id)
    rows = await run(
        session,
        """
        MATCH (reg:Registration {id: $registration_id})-[:FOR_CYCLE]->(ac:AcademicCycle)
        MATCH (reg)-[:OPENS]->(g:Group)-[:OF_SUBJECT]->(su:Subject)
        RETURN
          su.code AS subject_code,
          su.name AS subject_name,
          g.g_type AS g_type,
          ac.year AS cycle_year,
          ac.season AS cycle_season
        """,
        registration_id=body.registration_id,
    )
    grouped: dict[str, CourseInRegistration] = {}
    counts: dict[str, dict[str, int]] = {}
    for row in rows:
        code = row["subject_code"]
        if code not in grouped:
            grouped[code] = CourseInRegistration(
                id=code,
                name=row["subject_name"],
                classes=[],
                academic_cycle=f"{row['cycle_year']} {row['cycle_season']}",
            )
            counts[code] = {}
        counts[code][row["g_type"]] = counts[code].get(row["g_type"], 0) + 1
    for code, course in grouped.items():
        course.classes = [ClassInfo(g_type=kind, count=count) for kind, count in counts[code].items()]
    return ShowCoursesInRegistrationResponse(courses=list(grouped.values()))


@router.post("/me/registrations/groups", response_model=OpenGroupsResponse)
async def show_groups(
    body: OpenGroupsRequest,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_student),
) -> OpenGroupsResponse:
    await _require_registration(session, caller.idx, body.registration_id)
    rows = await run(
        session,
        """
        MATCH (st:Student {idx: $student_idx})
        MATCH (reg:Registration {id: $registration_id})-[:OPENS]->(g:Group)-[:OF_SUBJECT]->(:Subject {code: $course_id})
        OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
        OPTIONAL MATCH (t:Teacher)-[:TEACHES]->(g)
        OPTIONAL MATCH (st)-[mine:REGISTERED_IN]->(g)
        RETURN
          g.id AS id,
          g.g_type AS g_type,
          g.number AS number,
          g.weekday AS weekday,
          g.start_hr AS start,
          g.end_time AS end,
          g.capacity AS capacity,
          size([(g)<-[:REGISTERED_IN]-() | 1]) AS filled,
          r.building + " " + r.room_num AS room,
          t.name + " " + t.surname AS teacher,
          mine IS NOT NULL AS registered
        ORDER BY g.g_type, g.number
        """,
        student_idx=caller.idx,
        registration_id=body.registration_id,
        course_id=body.course_id,
    )
    return OpenGroupsResponse(groups=[OpenGroup(**row) for row in rows])


@router.post("/me/registrations/register", response_model=RegisterToGroupResponse)
async def register_to_group(
    body: RegisterToGroupRequest,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_student),
) -> RegisterToGroupResponse:
    row = await one(
        session,
        """
        MATCH (st:Student {idx: $student_idx})-[:ASSIGNED]->(:TurnAssignment)-[:FOR_TURN]->(:RegistrationTurn)<-[:HAS_TURN]-(:Registration)-[:OPENS]->(g:Group {id: $group_id})-[:OF_SUBJECT]->(:Subject {code: $course_id})
        MERGE (st)-[r:REGISTERED_IN]->(g)
          ON CREATE SET r.registered_at = datetime()
        RETURN g.id AS group_id
        """,
        student_idx=caller.idx,
        group_id=body.group_id,
        course_id=body.course_id,
    )
    if row is None:
        raise HTTPException(status_code=403, detail="Forbidden")
    return RegisterToGroupResponse(ok=True)


@router.get("/me/enrolments", response_model=MyEnrolmentsResponse)
async def my_enrolments(
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_student),
) -> MyEnrolmentsResponse:
    rows = await run(
        session,
        """
        MATCH (st:Student {idx: $student_idx})-[:ENROLLED]->(ct:CurriculumTerm)<-[:HAS_TERM]-(c:Curriculum)<-[:HAS_CURRICULUM]-(p:Programme)
        OPTIONAL MATCH (ct)-[:TAUGHT_IN]->(ac:AcademicCycle)
        RETURN
          p.id AS programme_id,
          p.name AS programme,
          c.id AS curriculum_id,
          c.intake_year AS intake_year,
          ct.id AS term_id,
          ct.sem AS sem,
          ac.id AS cycle_id,
          ac.year AS year,
          ac.season AS season
        ORDER BY p.name, ct.sem
        """,
        student_idx=caller.idx,
    )
    return MyEnrolmentsResponse(enrolments=[Enrolment(**row) for row in rows])


@router.get("/me/academic-cycles", response_model=MyAcademicCyclesResponse)
async def my_cycles(
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_student),
) -> MyAcademicCyclesResponse:
    rows = await run(
        session,
        """
        MATCH (st:Student {idx: $student_idx})-[:ENROLLED]->(:CurriculumTerm)-[:TAUGHT_IN]->(ac:AcademicCycle)
        RETURN DISTINCT ac.id AS id, ac.year AS year, ac.season AS season
        """,
        student_idx=caller.idx,
    )
    return MyAcademicCyclesResponse(cycles=[MyAcademicCycleItem(**row) for row in rows])


@router.post("/me/academic-cycles/detail", response_model=MyAcademicCycleDetailResponse)
async def my_cycle_detail(
    body: MyAcademicCycleDetailRequest,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_student),
) -> MyAcademicCycleDetailResponse:
    row = await one(
        session,
        """
        MATCH (:Student {idx: $student_idx})-[:ENROLLED]->(:CurriculumTerm)-[:TAUGHT_IN]->(ac:AcademicCycle {id: $cycle_id})
        RETURN ac.id AS id, ac.year AS year, ac.season AS season
        """,
        student_idx=caller.idx,
        cycle_id=body.cycle_id,
    )
    if row is None:
        raise HTTPException(status_code=403, detail="Forbidden")
    return MyAcademicCycleDetailResponse(**row)


@router.get("/me/dashboard", response_model=DashboardResponse)
async def dashboard(
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_student),
) -> DashboardResponse:
    rows = await run(
        session,
        """
        MATCH (st:Student {idx: $student_idx})-[:REGISTERED_IN]->(g:Group)-[:OF_SUBJECT]->(su:Subject)
        OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
        OPTIONAL MATCH (reg:Registration)-[:OPENS]->(g)
        OPTIONAL MATCH (reg)-[:FOR_CYCLE]->(ac:AcademicCycle)
        RETURN
          su.code AS course_code,
          su.name AS course_name,
          g.g_type AS g_type,
          g.number AS number,
          g.weekday AS weekday,
          g.start_hr AS start,
          g.end_time AS end,
          r.building + " " + r.room_num AS room,
          ac.year + " " + ac.season AS cycle
        """,
        student_idx=caller.idx,
    )
    return DashboardResponse(groups=[RegisteredGroup(**row) for row in rows])


@router.post("/opinions", response_model=OpinionCreateResponse)
async def create_opinion(
    body: OpinionCreateRequest,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_opinion_roles),
) -> OpinionCreateResponse:
    student_idx = caller.idx if caller.role == "Student" else body.student_idx
    if not student_idx:
        return OpinionCreateResponse(
            id=0,
            grade=body.grade,
            content=body.content,
            submit=body.submit,
            group_id=body.group_id,
            err="student_idx is required",
        )
    opinion_id = await next_id(session, "Opinion")
    row = await one(
        session,
        """
        MATCH (st:Student {idx: $student_idx})-[:REGISTERED_IN]->(g:Group {id: $group_id})
        CREATE (o:Opinion {id: $id, grade: $grade, content: $content, submit: datetime($submit)})
        CREATE (st)-[:WRITES]->(o)
        CREATE (o)-[:ABOUT]->(g)
        RETURN o.id AS id, o.grade AS grade, o.content AS content, o.submit AS submit, g.id AS group_id
        """,
        student_idx=student_idx,
        group_id=body.group_id,
        id=opinion_id,
        grade=body.grade,
        content=body.content,
        submit=_zoned_datetime(body.submit),
    )
    if row is None:
        raise HTTPException(status_code=403, detail="Forbidden")
    return OpinionCreateResponse(**row)
