from fastapi import APIRouter, Depends, HTTPException
from neo4j import AsyncSession

from app.database import get_session
from app.graph_backend.auth import Caller, require
from app.graph_backend.query import run
from app.schemas.curriculum import (
    CurriculumCatalogueItem,
    CurriculumCatalogueResponse,
)
from app.schemas.generic import TeacherNameRef
from app.schemas.group import GroupDetailRequest, GroupDetailResponse, GroupTracked
from app.schemas.subject import (
    SubjectCatalogueItem,
    SubjectCatalogueResponse,
    SubjectCycleCell,
    SubjectDetailRequest,
    SubjectDetailResponse,
    SubjectGroupsRequest,
    SubjectGroupsResponse,
)
from app.schemas.subject_instance import SubjectInstanceItem
from app.schemas.teacher import (
    TeacherCatalogueItem,
    TeacherCatalogueResponse,
    TeacherDetailRequest,
    TeacherDetailResponse,
)
from app.schemas.faculty import FacultyItem, FacultyListResponse
from app.schemas.teacher import GroupAndCourse

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
ORDER BY ac.year, ac.season
"""

_SUBJECTS = """
MATCH (su:Subject)
WHERE ($name IS NULL OR toLower(su.name) CONTAINS toLower($name))
  AND ($code IS NULL OR toLower(su.code) CONTAINS toLower($code))
OPTIONAL MATCH (su)<-[:INCLUDES]-(:CurriculumTerm)<-[:HAS_TERM]-(:Curriculum)<-[:HAS_CURRICULUM]-(:Programme)-[:OFFERED_BY]->(fa:Faculty)
WITH su, collect(DISTINCT fa.name) AS faculty_names
OPTIONAL MATCH (su)<-[:INSTANCE_OF]-(si:SubjectInstance)-[:OFFERED_IN]->(ac:AcademicCycle)
OPTIONAL MATCH (si)-[:HAS_GROUP]->(g:Group)
OPTIONAL MATCH (reg:Registration)-[:FOR_CYCLE]->(ac)
OPTIONAL MATCH (reg)-[:OPENS]->(g)
RETURN
  su.code AS subject_code,
  su.name AS subject_name,
  su.ects AS ects,
  faculty_names,
  si.id AS instance_id,
  si.catalogue_code AS catalogue_code,
  ac.id AS cycle_id,
  ac.year AS cycle_year,
  ac.season AS cycle_season,
  count(DISTINCT g) AS group_count,
  count(DISTINCT reg) > 0 AS registration_open
ORDER BY su.name, ac.year, ac.season
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
    cycle_columns: list[str],
    cycle_ids: list[str],
    rows: list[dict],
) -> list[SubjectCatalogueItem]:
    grouped: dict[str, SubjectCatalogueItem] = {}
    cycle_index = {cid: idx for idx, cid in enumerate(cycle_ids)}
    for row in rows:
        code = row["subject_code"]
        item = grouped.get(code)
        if item is None:
            item = SubjectCatalogueItem(
                code=code,
                name=row["subject_name"],
                ects=row["ects"],
                faculty=_faculty_label(row.get("faculty_names")),
                catalogue_code=row.get("catalogue_code") or "",
                cycles=[SubjectCycleCell() for _ in cycle_columns],
            )
            grouped[code] = item
        cycle_id = row.get("cycle_id")
        instance_id = row.get("instance_id")
        if cycle_id and instance_id and cycle_id in cycle_index:
            idx = cycle_index[cycle_id]
            if row.get("catalogue_code") and not item.catalogue_code:
                item.catalogue_code = row["catalogue_code"]
            item.cycles[idx] = SubjectCycleCell(
                instance_id=instance_id,
                group_count=row.get("group_count") or 0,
                registration_open=bool(row.get("registration_open")),
            )
    return list(grouped.values())


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
    cycle_rows = await run(session, _ACADEMIC_CYCLES)
    cycle_columns = [
        _cycle_column(row["year"], row["season"]) for row in cycle_rows
    ]
    cycle_ids = [row["id"] for row in cycle_rows]
    rows = await run(session, _SUBJECTS, name=name, code=code)
    return SubjectCatalogueResponse(
        cycle_columns=cycle_columns,
        subjects=_subject_catalogue(cycle_columns, cycle_ids, rows),
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
    base_rows = await run(
        session,
        """
        MATCH (s:Subject {code: $code})
        OPTIONAL MATCH (s)-[:HAS_TYPE]->(:GroupType)<-[:OF_TYPE]-(:Group)<-[:TEACHES]-(t:Teacher)
        RETURN
          s.code AS code,
          s.name AS name,
          s.ects AS ects,
          t.idx AS teacher_idx,
          t.name AS teacher_name,
          t.surname AS teacher_surname
        """,
        code=body.code,
    )
    if not base_rows:
        raise HTTPException(status_code=404, detail="Subject not found")
    taught = []
    seen = set()
    for row in base_rows:
        if row["teacher_idx"] and row["teacher_idx"] not in seen:
            seen.add(row["teacher_idx"])
            taught.append(
                TeacherNameRef(
                    id=row["teacher_idx"],
                    name=f"{row['teacher_name']} {row['teacher_surname']}",
                )
            )
    instance_rows = await run(
        session,
        """
        MATCH (s:Subject {code: $code})<-[:INSTANCE_OF]-(si:SubjectInstance)-[:OFFERED_IN]->(ac:AcademicCycle)
        OPTIONAL MATCH (si)-[:HAS_GROUP]->(g:Group)
        RETURN
          si.id AS instance_id,
          si.catalogue_code AS catalogue_code,
          ac.year AS cycle_year,
          ac.season AS cycle_season,
          count(g) AS group_count
        ORDER BY ac.year, ac.season
        """,
        code=body.code,
    )
    instances = [
        SubjectInstanceItem(
            id=row["instance_id"],
            cycle=_cycle(row["cycle_year"], row["cycle_season"]),
            catalogue_code=row.get("catalogue_code") or "",
            group_count=row.get("group_count") or 0,
        )
        for row in instance_rows
        if row.get("instance_id")
    ]
    first = base_rows[0]
    return SubjectDetailResponse(
        code=first["code"],
        name=first["name"],
        ects=first["ects"],
        taught_by=taught,
        instances=instances,
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
        MATCH (si:SubjectInstance {id: $instance_id})-[:INSTANCE_OF]->(su:Subject)
        MATCH (si)-[:OFFERED_IN]->(ac:AcademicCycle)
        MATCH (si)-[:HAS_GROUP]->(g:Group)-[:OF_TYPE]->(gt:GroupType)
        OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
        OPTIONAL MATCH (st:Student)-[:REGISTERED_IN]->(g)
        RETURN
          su.name AS subject_name,
          si.id AS instance_id,
          ac.year AS cycle_year,
          ac.season AS cycle_season,
          g.id AS id,
          g.weekday AS weekday,
          gt.g_type AS g_type,
          g.number AS number,
          g.pnp AS pnp,
          g.capacity AS capacity,
          g.start_hr AS start_hr,
          g.end_time AS end_time,
          r.building AS building,
          r.room_num AS room_num,
          count(st) AS filled
        ORDER BY gt.g_type, g.weekday, g.start_hr, g.number
        """,
        instance_id=body.instance_id,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Subject instance not found")
    groups = []
    seen = set()
    for row in rows:
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        groups.append(
            GroupTracked(
                id=row["id"],
                weekday=row["weekday"],
                g_type=row["g_type"],
                number=row["number"],
                pnp=row["pnp"],
                capacity=row["capacity"],
                start_hr=row["start_hr"],
                end_time=row["end_time"],
                cycle=_cycle(row["cycle_year"], row["cycle_season"]),
                room=_room(row["building"], row["room_num"]),
                filled=row["filled"],
            )
        )
    return SubjectGroupsResponse(
        name=rows[0]["subject_name"],
        instance_id=rows[0]["instance_id"],
        cycle=_cycle(rows[0]["cycle_year"], rows[0]["cycle_season"]),
        groups=groups,
    )


@router.post("/groups/detail", response_model=GroupDetailResponse)
async def group_detail(
    body: GroupDetailRequest,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_logged_in),
) -> GroupDetailResponse:
    rows = await run(
        session,
        """
        MATCH (g:Group {id: $group_id})<-[:HAS_GROUP]-(si:SubjectInstance)-[:INSTANCE_OF]->(su:Subject)
        MATCH (g)-[:OF_TYPE]->(gt:GroupType)
        MATCH (si)-[:OFFERED_IN]->(ac:AcademicCycle)
        OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
        OPTIONAL MATCH (t:Teacher)-[:TEACHES]->(g)
        OPTIONAL MATCH (st:Student)-[:REGISTERED_IN]->(g)
        RETURN
          su.code AS subject_code,
          su.name AS course_name,
          gt.g_type AS g_type,
          g.number AS group_num,
          g.weekday AS weekday,
          g.pnp AS pnp,
          g.start_hr AS start_hr,
          g.end_time AS end_time,
          g.capacity AS capacity,
          r.building AS building,
          r.room_num AS room_num,
          ac.year AS cycle_year,
          ac.season AS cycle_season,
          t.idx AS teacher_idx,
          t.name AS teacher_name,
          t.surname AS teacher_surname,
          count(st) AS filled
        """,
        group_id=body.group_id,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Group not found")
    row = rows[0]
    teacher = TeacherNameRef(id="", name="")
    if row["teacher_idx"]:
        teacher = TeacherNameRef(
            id=row["teacher_idx"],
            name=f"{row['teacher_name']} {row['teacher_surname']}",
        )
    return GroupDetailResponse(
        subject_code=row["subject_code"] or "",
        course_name=row["course_name"],
        g_type=row["g_type"],
        academic_cycle=_cycle(row["cycle_year"], row["cycle_season"]),
        group_num=row["group_num"],
        weekday=row["weekday"],
        pnp=row["pnp"] or "",
        start_hr=row["start_hr"],
        end_time=row["end_time"],
        room=_room(row["building"], row["room_num"]),
        building=row["building"] or "",
        nearest_classes=[],
        filled=row["filled"],
        capacity=row["capacity"],
        teacher=teacher,
    )


@router.post("/teachers/detail", response_model=TeacherDetailResponse)
async def teacher_detail(
    body: TeacherDetailRequest,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_logged_in),
) -> TeacherDetailResponse:
    rows = await run(
        session,
        """
        MATCH (t:Teacher {idx: $idx})
        OPTIONAL MATCH (t)-[:TEACHES]->(g:Group)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(su:Subject)
        OPTIONAL MATCH (g)<-[:HAS_GROUP]-(:SubjectInstance)-[:OFFERED_IN]->(ac:AcademicCycle)
        RETURN
          t.degree AS degree,
          t.name AS name,
          t.surname AS surname,
          t.email AS email,
          t.phone AS phone,
          g.id AS group_id,
          su.code AS course_code,
          su.name AS course_name,
          gt.g_type AS g_type,
          g.number AS group_num,
          ac.year AS cycle_year,
          ac.season AS cycle_season
        """,
        idx=body.idx,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Teacher not found")
    groups = []
    for row in rows:
        if row["group_id"] is None:
            continue
        groups.append(
            GroupAndCourse(
                group_id=row["group_id"],
                course_code=row["course_code"] or "",
                course_name=row["course_name"] or "",
                g_type=row["g_type"],
                group_num=row["group_num"],
                academic_cycle=_cycle(row.get("cycle_year"), row.get("cycle_season")),
            )
        )
    first = rows[0]
    return TeacherDetailResponse(
        degree=first["degree"],
        name=f"{first['name']} {first['surname']}",
        phone=first["phone"],
        email=first["email"],
        groups=groups,
    )
