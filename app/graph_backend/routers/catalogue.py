from fastapi import APIRouter, Depends
from neo4j import AsyncSession

from app.graph_backend.database import get_session
from app.graph_backend.auth import Caller, require
from app.graph_backend.errors import invalid, not_found
from app.graph_backend.cycles import cycle_sort_key
from app.graph_backend.query import one, run
from app.graph_backend.teaching import teacher_groups
from app.schemas.curriculum import (
    CurriculumCatalogueItem,
    CurriculumCatalogueResponse,
)
from app.schemas.generic import TeacherNameRef
from app.schemas.group import GroupDetailResponse, GroupTracked
from app.schemas.opinion import OpinionItem, OpinionListResponse
from app.schemas.subject import (
    SubjectCatalogueItem,
    SubjectCatalogueResponse,
    SubjectDetailResponse,
    SubjectGroupsResponse,
    SubjectOfferingItem,
)
from app.schemas.teacher import (
    MyTeachingGroupsResponse,
    TeacherCatalogueItem,
    TeacherCatalogueResponse,
    TeacherDetailResponse,
)
from app.schemas.faculty import FacultyItem, FacultyListResponse

router = APIRouter(tags=["catalogue"])
_logged_in = require("Student", "Teacher", "Admin")


def _cycle(year, season) -> str:
    if year and season:
        return f"{year} {season}"
    return ""


def _room(building, room_num) -> str:
    if building and room_num:
        return f"{building} {room_num}"
    return ""


_TEACHERS = """
MATCH (t:Teacher)
WHERE $name IS NULL
   OR toLower(t.name + " " + t.surname) CONTAINS toLower($name)
OPTIONAL MATCH (t)-[:WORKS_AT]->(fa:Faculty)
RETURN
  t.idx AS idx,
  t.name AS name,
  t.surname AS surname,
  t.phone AS phone,
  t.degree AS degree,
  t.photo AS photo,
  t.working_since AS working_since,
  fa.name AS faculty
ORDER BY t.surname, t.name
"""

_ACADEMIC_CYCLES = """
MATCH (ac:AcademicCycle)
RETURN ac.id AS id, ac.year AS year, ac.season AS season
"""

# One row per subject; `cycles` holds one cell per id in $cycle_ids, in the same order.
_SUBJECTS = """
MATCH (su:Subject)
WHERE ($name IS NULL OR toLower(su.name) CONTAINS toLower($name))
  AND ($code IS NULL OR toLower(su.code) CONTAINS toLower($code))
RETURN
  su.code AS code,
  su.name AS name,
  su.ects AS ects,
  COLLECT {
    MATCH (su)<-[:INCLUDES]-(:CurriculumTerm)<-[:HAS_TERM]-(:Curriculum)<-[:HAS_CURRICULUM]-(:Programme)-[:OFFERED_BY]->(fa:Faculty)
    RETURN DISTINCT fa.name
  } AS faculties,
  [cycle_id IN $cycle_ids | {
    offered: EXISTS {
      (su)<-[:INCLUDES]-(:CurriculumTerm)-[:TAUGHT_IN]->(:AcademicCycle {id: cycle_id})
    },
    group_count: COUNT {
      (su)<-[:INSTANCE_OF]-(si:SubjectInstance)-[:OFFERED_IN]->(:AcademicCycle {id: cycle_id}),
      (si)-[:HAS_TYPE]->(:GroupType)<-[:OF_TYPE]-(:Group)
    },
    // Registration has no dates of its own: its period runs from the start of its first turn
    // to the end of its last one.
    registration_open: EXISTS {
      MATCH (su)<-[:INSTANCE_OF]-(si:SubjectInstance)-[:OFFERED_IN]->(:AcademicCycle {id: cycle_id}),
            (si)-[:HAS_TYPE]->(:GroupType)<-[:OF_TYPE]-(:Group)<-[:OPENS]-(reg:Registration)-[:HAS_TURN]->(rt:RegistrationTurn)
      WITH reg,
           min(datetime({date: rt.date, time: rt.start_time, timezone: 'Europe/Warsaw'})) AS opens,
           max(datetime({date: rt.date, time: rt.end_time, timezone: 'Europe/Warsaw'})) AS closes
      WHERE opens <= datetime() < closes
    }
  }] AS cycles
ORDER BY su.name
"""

_ORGANIZATIONAL_UNITS = """
MATCH (fa:Faculty)
WHERE $name IS NULL
   OR toLower(fa.name) CONTAINS toLower($name)
   OR toLower(fa.full_name) CONTAINS toLower($name)
RETURN fa.id AS id, fa.name AS name, fa.full_name AS full_name
ORDER BY fa.name
"""

_CURRICULA = """
MATCH (p:Programme)-[:HAS_CURRICULUM]->(c:Curriculum)
WHERE ($name IS NULL OR toLower(p.name) CONTAINS toLower($name))
RETURN
  c.id AS id,
  p.id AS programme_id,
  p.name AS name,
  c.intake_year AS intake_year
ORDER BY p.name, c.intake_year DESC
"""


def _cycle_column(year: str | None, season: str | None) -> str:
    if year and season:
        return f"{year}-{season}"
    return ""


def _faculty_label(names: list | None) -> str:
    if not names:
        return ""
    parts = sorted({n for n in names if n})
    return ", ".join(parts)


@router.get("/teachers", response_model=TeacherCatalogueResponse)
async def teacher_catalogue(
    name: str | None = None,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_logged_in),
) -> TeacherCatalogueResponse:
    rows = await run(session, _TEACHERS, name=name)
    for row in rows:
        row["faculty"] = row["faculty"] or ""
    return TeacherCatalogueResponse(
        teachers=[TeacherCatalogueItem(**row) for row in rows]
    )


@router.get("/subjects", response_model=SubjectCatalogueResponse)
async def subject_catalogue(
    name: str | None = None,
    code: str | None = None,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_logged_in),
) -> SubjectCatalogueResponse:
    cycle_rows = sorted(
        await run(session, _ACADEMIC_CYCLES),
        key=lambda row: cycle_sort_key(row["year"], row["season"]),
    )
    rows = await run(
        session, _SUBJECTS, name=name, code=code, cycle_ids=[row["id"] for row in cycle_rows]
    )
    for row in rows:
        row["faculty"] = _faculty_label(row.pop("faculties"))
    return SubjectCatalogueResponse(
        cycle_columns=[_cycle_column(row["year"], row["season"]) for row in cycle_rows],
        subjects=[SubjectCatalogueItem(**row) for row in rows],
    )


@router.get("/faculties", response_model=FacultyListResponse)
async def organizational_units_catalogue(
    name: str | None = None,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_logged_in),
) -> FacultyListResponse:
    rows = await run(session, _ORGANIZATIONAL_UNITS, name=name)
    return FacultyListResponse(faculties=[FacultyItem(**row) for row in rows])


@router.get("/curricula", response_model=CurriculumCatalogueResponse)
async def curriculum_catalogue(
    name: str | None = None,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_logged_in),
) -> CurriculumCatalogueResponse:
    rows = await run(session, _CURRICULA, name=name)
    return CurriculumCatalogueResponse(
        curricula=[CurriculumCatalogueItem(**row) for row in rows]
    )


@router.get("/subjects/{code}", response_model=SubjectDetailResponse)
async def subject_detail(
    code: str,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_logged_in),
) -> SubjectDetailResponse:
    subject = await one(
        session,
        """
        MATCH (s:Subject {code: $code})
        RETURN
          s.code AS code,
          s.name AS name,
          s.ects AS ects,
          COLLECT {
            MATCH (s)<-[:INSTANCE_OF]-(:SubjectInstance)-[:HAS_TYPE]->(:GroupType)<-[:OF_TYPE]-(:Group)<-[:TEACHES]-(t:Teacher)
            RETURN DISTINCT {id: t.idx, name: t.name + " " + t.surname}
          } AS taught_by
        """,
        code=code,
    )
    if subject is None:
        raise not_found("Subject")
    offering_rows = await run(
        session,
        """
        MATCH (s:Subject {code: $code})<-[:INCLUDES]-(:CurriculumTerm)-[:TAUGHT_IN]->(ac:AcademicCycle)
        WITH DISTINCT s, ac
        RETURN
          ac.id AS cycle_id,
          ac.year AS cycle_year,
          ac.season AS cycle_season,
          COUNT {
            (s)<-[:INSTANCE_OF]-(si:SubjectInstance)-[:OFFERED_IN]->(ac),
            (si)-[:HAS_TYPE]->(:GroupType)<-[:OF_TYPE]-(:Group)
          } AS group_count
        """,
        code=code,
    )
    offering_rows.sort(key=lambda row: cycle_sort_key(row["cycle_year"], row["cycle_season"]))
    return SubjectDetailResponse(
        code=subject["code"],
        name=subject["name"],
        ects=subject["ects"],
        taught_by=[TeacherNameRef(**t) for t in subject["taught_by"]],
        offerings=[
            SubjectOfferingItem(
                cycle_id=row["cycle_id"],
                cycle=_cycle(row["cycle_year"], row["cycle_season"]),
                group_count=row["group_count"],
            )
            for row in offering_rows
        ],
    )


@router.get("/subjects/{subject_code}/groups", response_model=SubjectGroupsResponse)
async def subject_groups(
    subject_code: str,
    cycle_id: str,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_logged_in),
) -> SubjectGroupsResponse:
    rows = await run(
        session,
        """
        MATCH (su:Subject {code: $subject_code})<-[:INSTANCE_OF]-(si:SubjectInstance)-[:OFFERED_IN]->(ac:AcademicCycle {id: $cycle_id})
        MATCH (si)-[:HAS_TYPE]->(gt:GroupType)<-[:OF_TYPE]-(g:Group)
        OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
        RETURN
          su.name AS subject_name,
          su.code AS subject_code,
          ac.id AS cycle_id,
          ac.year AS cycle_year,
          ac.season AS cycle_season,
          g.id AS id,
          g.weekday AS weekday,
          gt.g_type AS g_type,
          g.number AS number,
          g.pnp AS pnp,
          g.capacity AS capacity,
          g.start_time AS start_time,
          g.end_time AS end_time,
          r.building AS building,
          r.room_num AS room_num,
          COUNT { (g)<-[:REGISTERED_IN]-(:Student) } AS filled
        ORDER BY gt.g_type, g.weekday, g.start_time, g.number
        """,
        subject_code=subject_code,
        cycle_id=cycle_id,
    )
    if not rows:
        raise not_found("Groups for this subject in this cycle")
    groups = [
        GroupTracked(
            id=row["id"],
            weekday=row["weekday"],
            g_type=row["g_type"],
            number=row["number"],
            pnp=row["pnp"],
            capacity=row["capacity"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            cycle=_cycle(row["cycle_year"], row["cycle_season"]),
            room=_room(row["building"], row["room_num"]),
            filled=row["filled"],
        )
        for row in rows
    ]
    return SubjectGroupsResponse(
        name=rows[0]["subject_name"],
        subject_code=rows[0]["subject_code"],
        cycle_id=rows[0]["cycle_id"],
        cycle=_cycle(rows[0]["cycle_year"], rows[0]["cycle_season"]),
        groups=groups,
    )


@router.get("/groups/{group_id}", response_model=GroupDetailResponse)
async def group_detail(
    group_id: str,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_logged_in),
) -> GroupDetailResponse:
    row = await one(
        session,
        """
        MATCH (g:Group {id: $group_id})-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(si:SubjectInstance)
        MATCH (si)-[:INSTANCE_OF]->(su:Subject)
        MATCH (si)-[:OFFERED_IN]->(ac:AcademicCycle)
        OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
        RETURN
          su.code AS subject_code,
          su.name AS course_name,
          gt.g_type AS g_type,
          g.number AS group_num,
          g.weekday AS weekday,
          g.pnp AS pnp,
          g.start_time AS start_time,
          g.end_time AS end_time,
          g.capacity AS capacity,
          r.building AS building,
          r.room_num AS room_num,
          ac.year AS cycle_year,
          ac.season AS cycle_season,
          COUNT { (g)<-[:REGISTERED_IN]-(:Student) } AS filled,
          COLLECT {
            MATCH (t:Teacher)-[:TEACHES]->(g)
            RETURN {id: t.idx, name: t.name + " " + t.surname}
          } AS teachers
        """,
        group_id=group_id,
    )
    if row is None:
        raise not_found("Group")
    return GroupDetailResponse(
        subject_code=row["subject_code"] or "",
        course_name=row["course_name"],
        g_type=row["g_type"],
        academic_cycle=_cycle(row["cycle_year"], row["cycle_season"]),
        group_num=row["group_num"],
        weekday=row["weekday"],
        pnp=row["pnp"] or "",
        start_time=row["start_time"],
        end_time=row["end_time"],
        room=_room(row["building"], row["room_num"]),
        building=row["building"] or "",
        nearest_classes=[],
        filled=row["filled"],
        capacity=row["capacity"],
        teachers=[TeacherNameRef(**t) for t in row["teachers"]],
    )


@router.get("/teachers/{idx}", response_model=TeacherDetailResponse)
async def teacher_detail(
    idx: str,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_logged_in),
) -> TeacherDetailResponse:
    profile = await one(
        session,
        """
        MATCH (t:Teacher {idx: $idx})
        RETURN t.degree AS degree, t.name AS name, t.surname AS surname, t.email AS email, t.phone AS phone
        """,
        idx=idx,
    )
    if profile is None:
        raise not_found("Teacher")
    return TeacherDetailResponse(
        degree=profile["degree"],
        name=f"{profile['name']} {profile['surname']}",
        phone=profile["phone"],
        email=profile["email"],
        groups=await teacher_groups(session, idx),
    )


# The same list as in GET /teachers/{idx}, on its own: the weekly schedule of any teacher.
@router.get("/teachers/{idx}/groups", response_model=MyTeachingGroupsResponse)
async def teacher_groups_list(
    idx: str,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_logged_in),
) -> MyTeachingGroupsResponse:
    if await one(session, "MATCH (t:Teacher {idx: $idx}) RETURN t.idx AS idx", idx=idx) is None:
        raise not_found("Teacher")
    return MyTeachingGroupsResponse(groups=await teacher_groups(session, idx))


# Opinions are pseudonymous: the author (WRITES) stays in the graph, as it enforces one opinion per
# group and teacher, but is never read here. Only the day of submission is returned: with the exact
# time a teacher could match an opinion to a student of a small group.
_OPINIONS = """
MATCH (o:Opinion)-[:ABOUT]->(g:Group), (o)-[:ABOUT_TEACHER]->(t:Teacher)
WHERE ($teacher_idx IS NULL OR t.idx = $teacher_idx)
  AND ($group_id IS NULL OR g.id = $group_id)
MATCH (g)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(si:SubjectInstance)-[:INSTANCE_OF]->(su:Subject)
MATCH (si)-[:OFFERED_IN]->(ac:AcademicCycle)
RETURN
  o.id AS id,
  o.grade AS grade,
  o.content AS content,
  date(o.submit) AS submit,
  g.id AS group_id,
  su.code AS course_code,
  su.name AS course_name,
  gt.g_type AS g_type,
  ac.year + " " + ac.season AS cycle,
  t.idx AS teacher_idx,
  t.name + " " + t.surname AS teacher
ORDER BY o.submit DESC
"""


@router.get("/opinions", response_model=OpinionListResponse)
async def list_opinions(
    teacher_idx: str | None = None,
    group_id: str | None = None,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_logged_in),
) -> OpinionListResponse:
    if not teacher_idx and not group_id:
        raise invalid("teacher_idx or group_id is required")
    rows = await run(session, _OPINIONS, teacher_idx=teacher_idx, group_id=group_id)
    opinions = [OpinionItem(**row) for row in rows]
    avg = sum(o.grade for o in opinions) / len(opinions) if opinions else None
    return OpinionListResponse(opinions=opinions, avg_grade=avg)
