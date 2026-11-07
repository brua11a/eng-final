from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from neo4j import AsyncSession
from neo4j.exceptions import Neo4jError

from app.database import get_session
from app.graph_backend.auth import Caller, require
from app.graph_backend.errors import db_err
from app.graph_backend.query import next_id, one, run
from app.schemas.academic_cycle import (
    CycleSubject,
    CycleSubjectGroup,
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
    DeregisterFromGroupRequest,
    DeregisterFromGroupResponse,
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
MATCH (st:Student {idx: $student_idx})-[:ASSIGNED]->(:RegistrationTurn)<-[:HAS_TURN]-(reg:Registration {id: $registration_id})
RETURN reg.id AS id
"""


# Rewriting capacity takes a write lock on the group, so concurrent registrations
# for the same group see each other's writes before the capacity check.
_REGISTER = """
MATCH (st:Student {idx: $student_idx})-[:ASSIGNED]->(:RegistrationTurn)<-[:HAS_TURN]-(:Registration)-[:OPENS]->(g:Group {id: $group_id})
MATCH (g)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(:SubjectInstance)-[:INSTANCE_OF]->(:Subject {code: $subject_code})
WITH DISTINCT st, g, gt
SET g.capacity = g.capacity
WITH st, g,
  EXISTS { (st)-[:REGISTERED_IN]->(g) } AS already,
  EXISTS {
    MATCH (st)-[:REGISTERED_IN]->(other:Group)-[:OF_TYPE]->(gt)
    WHERE other <> g
  } AS conflict,
  COUNT { (g)<-[:REGISTERED_IN]-(:Student) } >= g.capacity AS full
WITH st, g, CASE
  WHEN already THEN "ok"
  WHEN conflict THEN "conflict"
  WHEN full THEN "full"
  ELSE "ok"
END AS status
FOREACH (_ IN CASE WHEN status = "ok" THEN [1] ELSE [] END |
  MERGE (st)-[r:REGISTERED_IN]->(g)
    ON CREATE SET r.registered_at = datetime()
)
RETURN status
"""


async def _require_registration(session: AsyncSession, student_idx: str, registration_id: str) -> None:
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
        MATCH (st:Student {idx: $student_idx})-[:ASSIGNED]->(rt:RegistrationTurn)<-[:HAS_TURN]-(reg:Registration)
        RETURN
          reg.id AS id,
          reg.name AS name,
          reg.reg_type AS reg_type,
          head(COLLECT {
            MATCH (reg)-[:FOR_FACULTY]->(:Faculty)<-[:OFFERED_BY]-(:Programme)-[:HAS_CURRICULUM]->(c:Curriculum)
                  -[:HAS_TERM]->(:CurriculumTerm)<-[:ENROLLED]-(st)
            RETURN c.id
          }) AS curriculum_id,
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
        MATCH (reg)-[:OPENS]->(g:Group)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(si:SubjectInstance)-[:OFFERED_IN]->(ac)
        MATCH (si)-[:INSTANCE_OF]->(su:Subject)
        RETURN
          su.code AS subject_code,
          su.name AS subject_name,
          gt.g_type AS g_type,
          ac.year AS cycle_year,
          ac.season AS cycle_season
        """,
        registration_id=body.registration_id,
    )
    grouped: dict[str, CourseInRegistration] = {}
    counts: dict[str, dict[str, int]] = {}
    for row in rows:
        iid = row["subject_code"]
        if iid not in grouped:
            grouped[iid] = CourseInRegistration(
                id=iid,
                name=row["subject_name"],
                classes=[],
                academic_cycle=f"{row['cycle_year']} {row['cycle_season']}",
            )
            counts[iid] = {}
        counts[iid][row["g_type"]] = counts[iid].get(row["g_type"], 0) + 1
    for iid, course in grouped.items():
        course.classes = [ClassInfo(g_type=kind, count=count) for kind, count in counts[iid].items()]
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
        MATCH (reg:Registration {id: $registration_id})-[:OPENS]->(g:Group)
        MATCH (g)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(:SubjectInstance)-[:INSTANCE_OF]->(:Subject {code: $subject_code})
        OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
        OPTIONAL MATCH (t:Teacher)-[:TEACHES]->(g)
        OPTIONAL MATCH (st)-[mine:REGISTERED_IN]->(g)
        RETURN
          g.id AS id,
          gt.g_type AS g_type,
          g.number AS number,
          g.weekday AS weekday,
          g.start_hr AS start,
          g.end_time AS end,
          g.capacity AS capacity,
          size([(g)<-[:REGISTERED_IN]-() | 1]) AS filled,
          r.building + " " + r.room_num AS room,
          t.name + " " + t.surname AS teacher,
          mine IS NOT NULL AS registered
        ORDER BY gt.g_type, g.number
        """,
        student_idx=caller.idx,
        registration_id=body.registration_id,
        subject_code=body.subject_code,
    )
    return OpenGroupsResponse(groups=[OpenGroup(**row) for row in rows])


@router.post("/me/registrations/register", response_model=RegisterToGroupResponse)
async def register_to_group(
    body: RegisterToGroupRequest,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_student),
) -> RegisterToGroupResponse:
    row = await one(session, _REGISTER, student_idx=caller.idx, group_id=body.group_id, subject_code=body.subject_code)
    if row is None:
        return RegisterToGroupResponse(ok=False, err="Forbidden")
    if row["status"] == "conflict":
        return RegisterToGroupResponse(
            ok=False,
            err="You are already registered in another group of this type for this subject",
        )
    if row["status"] == "full":
        return RegisterToGroupResponse(ok=False, err="Group is full")
    return RegisterToGroupResponse(ok=True)


@router.post("/me/registrations/deregister", response_model=DeregisterFromGroupResponse)
async def deregister_from_group(
    body: DeregisterFromGroupRequest,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_student),
) -> DeregisterFromGroupResponse:
    row = await one(
        session,
        """
        MATCH (st:Student {idx: $student_idx})-[r:REGISTERED_IN]->(g:Group {id: $group_id})
        MATCH (g)-[:OF_TYPE]->(:GroupType)<-[:HAS_TYPE]-(:SubjectInstance)-[:INSTANCE_OF]->(:Subject {code: $subject_code})
        MATCH (st)-[:ASSIGNED]->(:RegistrationTurn)<-[:HAS_TURN]-(:Registration)-[:OPENS]->(g)
        DELETE r
        RETURN g.id AS group_id
        """,
        student_idx=caller.idx,
        group_id=body.group_id,
        subject_code=body.subject_code,
    )
    if row is None:
        return DeregisterFromGroupResponse(ok=False, err="Not registered or registration closed")
    return DeregisterFromGroupResponse(ok=True)


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

    subject_rows = await run(
        session,
        """
        MATCH (:Student {idx: $student_idx})-[:ENROLLED]->(ct:CurriculumTerm)-[:TAUGHT_IN]->(:AcademicCycle {id: $cycle_id})
        MATCH (ct)-[:INCLUDES]->(su:Subject)
        RETURN DISTINCT su.code AS code, su.name AS name, su.ects AS ects
        """,
        student_idx=caller.idx,
        cycle_id=body.cycle_id,
    )
    group_rows = await run(
        session,
        """
        MATCH (st:Student {idx: $student_idx})-[reg:REGISTERED_IN]->(g:Group)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(si:SubjectInstance)
        MATCH (si)-[:OFFERED_IN]->(:AcademicCycle {id: $cycle_id})
        MATCH (si)-[:INSTANCE_OF]->(su:Subject)
        OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
        OPTIONAL MATCH (t:Teacher)-[:TEACHES]->(g)
        RETURN
          su.code AS code,
          su.name AS name,
          su.ects AS ects,
          g.id AS id,
          gt.g_type AS g_type,
          g.number AS number,
          g.weekday AS weekday,
          g.start_hr AS start,
          g.end_time AS end,
          r.building + " " + r.room_num AS room,
          t.name + " " + t.surname AS teacher,
          reg.grade AS grade
        ORDER BY su.name, gt.g_type, g.number
        """,
        student_idx=caller.idx,
        cycle_id=body.cycle_id,
    )

    subjects: dict[str, CycleSubject] = {}
    for s in subject_rows:
        subjects[s["code"]] = CycleSubject(code=s["code"], name=s["name"], ects=s["ects"])
    for g in group_rows:
        subject = subjects.setdefault(
            g["code"], CycleSubject(code=g["code"], name=g["name"], ects=g["ects"])
        )
        subject.groups.append(
            CycleSubjectGroup(
                id=g["id"],
                g_type=g["g_type"],
                number=g["number"],
                weekday=g["weekday"],
                start=g["start"],
                end=g["end"],
                room=g["room"],
                teacher=g["teacher"],
                grade=g["grade"],
            )
        )

    return MyAcademicCycleDetailResponse(
        **row,
        subjects=sorted(subjects.values(), key=lambda s: s.name),
    )


@router.get("/me/dashboard", response_model=DashboardResponse)
async def dashboard(
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_student),
) -> DashboardResponse:
    rows = await run(
        session,
        """
        MATCH (st:Student {idx: $student_idx})-[:REGISTERED_IN]->(g:Group)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(si:SubjectInstance)
        MATCH (si)-[:INSTANCE_OF]->(su:Subject)
        MATCH (si)-[:OFFERED_IN]->(ac:AcademicCycle)
        OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
        RETURN
          g.id AS group_id,
          su.code AS course_code,
          su.name AS course_name,
          gt.g_type AS g_type,
          g.number AS number,
          g.weekday AS weekday,
          g.start_hr AS start,
          g.end_time AS end,
          g.pnp AS pnp,
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
    if "Admin" in caller.roles and body.student_idx:
        student_idx = body.student_idx
    elif "Student" in caller.roles:
        student_idx = caller.idx
    else:
        student_idx = body.student_idx
    if not student_idx:
        return OpinionCreateResponse(
            grade=body.grade,
            content=body.content,
            submit=body.submit,
            group_id=body.group_id,
            err="student_idx is required",
        )
    opinion_id = await next_id(session, "Opinion")
    try:
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
    except Neo4jError as exc:
        return OpinionCreateResponse(
            grade=body.grade,
            content=body.content,
            submit=body.submit,
            group_id=body.group_id,
            err=db_err(exc),
        )
    if row is None:
        return OpinionCreateResponse(
            grade=body.grade,
            content=body.content,
            submit=body.submit,
            group_id=body.group_id,
            err="Forbidden",
        )
    return OpinionCreateResponse(**row)
