from fastapi import APIRouter, Depends, HTTPException
from neo4j import AsyncSession

from app.database import get_session
from app.graph_backend.auth import Caller, require
from app.graph_backend.cycles import cycle_sort_key
from app.graph_backend.query import one, run
from app.graph_backend.teaching import teacher_groups
from app.schemas.curriculum import (
    CurriculumCatalogueItem,
    CurriculumCatalogueResponse,
)
from app.schemas.generic import TeacherNameRef
from app.schemas.group import GroupDetailRequest, GroupDetailResponse, GroupTracked
from app.schemas.opinion import OpinionItem, OpinionListRequest, OpinionListResponse
from app.schemas.subject import (
    SubjectCatalogueItem,
    SubjectCatalogueResponse,
    SubjectCycleCell,
    SubjectDetailRequest,
    SubjectDetailResponse,
    SubjectGroupsRequest,
    SubjectGroupsResponse,
    SubjectOfferingItem,
)
from app.schemas.teacher import (
    TeacherCatalogueItem,
    TeacherCatalogueResponse,
    TeacherDetailRequest,
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
  } AS faculties
ORDER BY su.name
"""

_SUBJECT_OFFERINGS = """
MATCH (su:Subject)<-[:INCLUDES]-(:CurriculumTerm)-[:TAUGHT_IN]->(ac:AcademicCycle)
WHERE su.code IN $codes
RETURN DISTINCT su.code AS subject, ac.id AS cycle
"""

_SUBJECT_GROUP_COUNTS = """
MATCH (su:Subject)<-[:INSTANCE_OF]-(si:SubjectInstance)-[:OFFERED_IN]->(ac:AcademicCycle)
MATCH (si)-[:HAS_TYPE]->(:GroupType)<-[:OF_TYPE]-(g:Group)
WHERE su.code IN $codes
RETURN
  su.code AS subject,
  ac.id AS cycle,
  count(g) AS group_count,
  sum(CASE WHEN EXISTS { (:Registration)-[:OPENS]->(g) } THEN 1 ELSE 0 END) > 0 AS registration_open
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


def _subject_catalogue(
    cycle_ids: list[str],
    subjects: list[dict],
    offerings: list[dict],
    group_counts: list[dict],
) -> list[SubjectCatalogueItem]:
    offered = {(row["subject"], row["cycle"]) for row in offerings}
    counts = {(row["subject"], row["cycle"]): row for row in group_counts}
    items = []
    for subject in subjects:
        cells = []
        for cycle_id in cycle_ids:
            key = (subject["code"], cycle_id)
            count = counts.get(key, {})
            cells.append(
                SubjectCycleCell(
                    offered=key in offered,
                    group_count=count.get("group_count", 0),
                    registration_open=bool(count.get("registration_open")),
                )
            )
        items.append(
            SubjectCatalogueItem(
                code=subject["code"],
                name=subject["name"],
                ects=subject["ects"],
                faculty=_faculty_label(subject["faculties"]),
                cycles=cells,
            )
        )
    return items


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
    subjects = await run(session, _SUBJECTS, name=name, code=code)
    codes = [row["code"] for row in subjects]
    offerings = await run(session, _SUBJECT_OFFERINGS, codes=codes)
    group_counts = await run(session, _SUBJECT_GROUP_COUNTS, codes=codes)
    return SubjectCatalogueResponse(
        cycle_columns=[_cycle_column(row["year"], row["season"]) for row in cycle_rows],
        subjects=_subject_catalogue(
            [row["id"] for row in cycle_rows], subjects, offerings, group_counts
        ),
    )


@router.get("/organizational-units", response_model=FacultyListResponse)
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


@router.post("/subjects/detail", response_model=SubjectDetailResponse)
async def subject_detail(
    body: SubjectDetailRequest,
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
        code=body.code,
    )
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
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
        code=body.code,
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


@router.post("/subjects/groups", response_model=SubjectGroupsResponse)
async def subject_groups(
    body: SubjectGroupsRequest,
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
        subject_code=body.subject_code,
        cycle_id=body.cycle_id,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No groups for this subject in this cycle")
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


@router.post("/groups/detail", response_model=GroupDetailResponse)
async def group_detail(
    body: GroupDetailRequest,
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
        group_id=body.group_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Group not found")
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


@router.post("/teachers/detail", response_model=TeacherDetailResponse)
async def teacher_detail(
    body: TeacherDetailRequest,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_logged_in),
) -> TeacherDetailResponse:
    profile = await one(
        session,
        """
        MATCH (t:Teacher {idx: $idx})
        RETURN t.degree AS degree, t.name AS name, t.surname AS surname, t.email AS email, t.phone AS phone
        """,
        idx=body.idx,
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return TeacherDetailResponse(
        degree=profile["degree"],
        name=f"{profile['name']} {profile['surname']}",
        phone=profile["phone"],
        email=profile["email"],
        groups=await teacher_groups(session, body.idx),
    )


# Opinions are anonymous: the author (WRITES) is never returned.
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
  o.submit AS submit,
  g.id AS group_id,
  su.code AS course_code,
  su.name AS course_name,
  gt.g_type AS g_type,
  ac.year + " " + ac.season AS cycle,
  t.idx AS teacher_idx,
  t.name + " " + t.surname AS teacher
ORDER BY o.submit DESC
"""


@router.post("/opinions/list", response_model=OpinionListResponse)
async def list_opinions(
    body: OpinionListRequest,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_logged_in),
) -> OpinionListResponse:
    if not body.teacher_idx and not body.group_id:
        raise HTTPException(status_code=400, detail="teacher_idx or group_id is required")
    rows = await run(session, _OPINIONS, teacher_idx=body.teacher_idx, group_id=body.group_id)
    opinions = [OpinionItem(**row) for row in rows]
    avg = sum(o.grade for o in opinions) / len(opinions) if opinions else None
    return OpinionListResponse(opinions=opinions, avg_grade=avg)
