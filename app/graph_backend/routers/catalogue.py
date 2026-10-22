from fastapi import APIRouter, Depends, HTTPException
from neo4j import AsyncSession

from app.database import get_session
from app.graph_backend.auth import Caller, require
from app.graph_backend.query import run
from app.schemas.curriculum import (
    CurriculumCatalogueItem,
    CurriculumCatalogueResponse,
    CurriculumFindRequest,
)
from app.schemas.generic import TeacherNameRef
from app.schemas.group import GroupDetailRequest, GroupDetailResponse, GroupNested, GroupTracked
from app.schemas.subject import (
    SubjectAndGroups,
    SubjectCatalogueResponse,
    SubjectDetailRequest,
    SubjectDetailResponse,
    SubjectFindRequest,
    SubjectGroupsRequest,
    SubjectGroupsResponse,
)
from app.schemas.teacher import (
    TeacherCatalogueItem,
    TeacherCatalogueResponse,
    TeacherDetailRequest,
    TeacherDetailResponse,
    TeacherFindRequest,
)
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

_SUBJECTS = """
MATCH (su:Subject)
WHERE ($name IS NULL OR toLower(su.name) CONTAINS toLower($name))
  AND ($code IS NULL OR toLower(su.code) CONTAINS toLower($code))
OPTIONAL MATCH (g:Group)-[:OF_SUBJECT]->(su)
OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
OPTIONAL MATCH (reg:Registration)-[:OPENS]->(g)
OPTIONAL MATCH (reg)-[:FOR_CYCLE]->(ac:AcademicCycle)
RETURN
  su.code AS subject_code,
  su.name AS subject_name,
  su.ects AS ects,
  g.id AS group_id,
  g.weekday AS weekday,
  g.g_type AS g_type,
  g.number AS number,
  g.pnp AS pnp,
  g.capacity AS capacity,
  g.start_hr AS start_hr,
  g.end_time AS end_time,
  r.building AS building,
  r.room_num AS room_num,
  ac.year AS cycle_year,
  ac.season AS cycle_season
ORDER BY su.name, g.g_type, g.number
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


def _group_nested(row: dict) -> GroupNested:
    return GroupNested(
        id=row["group_id"],
        weekday=row["weekday"],
        g_type=row["g_type"],
        number=row["number"],
        pnp=row["pnp"],
        capacity=row["capacity"],
        start_hr=row["start_hr"],
        end_time=row["end_time"],
        cycle=_cycle(row["cycle_year"], row["cycle_season"]),
        room=_room(row["building"], row["room_num"]),
    )


def _subjects(rows: list[dict]) -> list[SubjectAndGroups]:
    grouped: dict[str, SubjectAndGroups] = {}
    seen: dict[str, set[int]] = {}
    for row in rows:
        code = row["subject_code"]
        item = grouped.get(code)
        if item is None:
            item = SubjectAndGroups(
                code=code,
                name=row["subject_name"],
                ects=row["ects"],
                groups=[],
            )
            grouped[code] = item
            seen[code] = set()
        group_id = row["group_id"]
        if group_id is not None and group_id not in seen[code]:
            seen[code].add(group_id)
            item.groups.append(_group_nested(row))
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


@router.post("/teachers/search", response_model=TeacherCatalogueResponse)
async def find_teachers(
    body: TeacherFindRequest,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_logged_in),
) -> TeacherCatalogueResponse:
    return await teacher_catalogue(body.name, session, caller)


@router.get("/subjects", response_model=SubjectCatalogueResponse)
async def subject_catalogue(
    name: str | None = None,
    code: str | None = None,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_logged_in),
) -> SubjectCatalogueResponse:
    rows = await run(session, _SUBJECTS, name=name, code=code)
    return SubjectCatalogueResponse(subject_and_groups=_subjects(rows))


@router.post("/subjects/search", response_model=SubjectCatalogueResponse)
async def find_subjects(
    body: SubjectFindRequest,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_logged_in),
) -> SubjectCatalogueResponse:
    return await subject_catalogue(body.name, body.code, session, caller)


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


@router.post("/curricula/search", response_model=CurriculumCatalogueResponse)
async def find_curricula(
    body: CurriculumFindRequest,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_logged_in),
) -> CurriculumCatalogueResponse:
    return await curriculum_catalogue(body.name, session, caller)


@router.post("/subjects/detail", response_model=SubjectDetailResponse)
async def subject_detail(
    body: SubjectDetailRequest,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_logged_in),
) -> SubjectDetailResponse:
    rows = await run(
        session,
        """
        MATCH (s:Subject {code: $code})
        OPTIONAL MATCH (s)<-[:OF_SUBJECT]-(:Group)<-[:TEACHES]-(t:Teacher)
        RETURN
          s.name AS name,
          s.ects AS ects,
          t.idx AS teacher_idx,
          t.name AS teacher_name,
          t.surname AS teacher_surname
        """,
        code=body.code,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Subject not found")
    taught = []
    seen = set()
    for row in rows:
        if row["teacher_idx"] and row["teacher_idx"] not in seen:
            seen.add(row["teacher_idx"])
            taught.append(
                TeacherNameRef(
                    id=row["teacher_idx"],
                    name=f"{row['teacher_name']} {row['teacher_surname']}",
                )
            )
    return SubjectDetailResponse(name=rows[0]["name"], ects=rows[0]["ects"], taught_by=taught)


@router.post("/subjects/groups", response_model=SubjectGroupsResponse)
async def subject_groups(
    body: SubjectGroupsRequest,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_logged_in),
) -> SubjectGroupsResponse:
    rows = await run(
        session,
        """
        MATCH (su:Subject {code: $code})<-[:OF_SUBJECT]-(g:Group)
        OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
        OPTIONAL MATCH (reg:Registration)-[:OPENS]->(g)
        OPTIONAL MATCH (reg)-[:FOR_CYCLE]->(ac:AcademicCycle)
        OPTIONAL MATCH (st:Student)-[:REGISTERED_IN]->(g)
        RETURN
          su.name AS subject_name,
          g.id AS id,
          g.weekday AS weekday,
          g.g_type AS g_type,
          g.number AS number,
          g.pnp AS pnp,
          g.capacity AS capacity,
          g.start_hr AS start_hr,
          g.end_time AS end_time,
          r.building AS building,
          r.room_num AS room_num,
          ac.year AS cycle_year,
          ac.season AS cycle_season,
          count(st) AS filled
        ORDER BY g.g_type, g.weekday, g.start_hr, g.number
        """,
        code=body.code,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Subject not found")
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
    return SubjectGroupsResponse(name=rows[0]["subject_name"], groups=groups)


@router.post("/groups/detail", response_model=GroupDetailResponse)
async def group_detail(
    body: GroupDetailRequest,
    session: AsyncSession = Depends(get_session),
    caller: Caller = Depends(_logged_in),
) -> GroupDetailResponse:
    rows = await run(
        session,
        """
        MATCH (su:Subject {code: $code})<-[:OF_SUBJECT]-(g:Group {number: $group_num, g_type: $g_type})
        OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
        OPTIONAL MATCH (reg:Registration)-[:OPENS]->(g)
        OPTIONAL MATCH (reg)-[:FOR_CYCLE]->(ac:AcademicCycle)
        OPTIONAL MATCH (t:Teacher)-[:TEACHES]->(g)
        OPTIONAL MATCH (st:Student)-[:REGISTERED_IN]->(g)
        RETURN
          su.name AS course_name,
          g.g_type AS g_type,
          g.number AS group_num,
          g.weekday AS weekday,
          g.start_hr AS start_hr,
          g.end_time AS end_time,
          g.capacity AS capacity,
          r.building AS building,
          ac.year AS cycle_year,
          ac.season AS cycle_season,
          t.idx AS teacher_idx,
          t.name AS teacher_name,
          t.surname AS teacher_surname,
          count(st) AS filled
        """,
        code=body.code,
        group_num=body.group_num,
        g_type=body.g_type,
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
        course_name=row["course_name"],
        g_type=row["g_type"],
        academic_cycle=_cycle(row["cycle_year"], row["cycle_season"]),
        group_num=row["group_num"],
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
        OPTIONAL MATCH (t)-[:TEACHES]->(g:Group)-[:OF_SUBJECT]->(su:Subject)
        RETURN
          t.degree AS degree,
          t.name AS name,
          t.surname AS surname,
          t.email AS email,
          t.phone AS phone,
          su.code AS course_code,
          g.g_type AS g_type,
          g.number AS group_num
        """,
        idx=body.idx,
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Teacher not found")
    groups = []
    for row in rows:
        if row["course_code"] is None:
            continue
        groups.append(
            GroupAndCourse(
                course_code=row["course_code"],
                g_type=row["g_type"],
                group_num=row["group_num"],
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
