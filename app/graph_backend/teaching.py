from neo4j import AsyncSession

from app.graph_backend.query import run
from app.schemas.teacher import TeachingGroupItem

_TEACHER_GROUPS = """
MATCH (t:Teacher {idx: $idx})-[:TEACHES]->(g:Group)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(si:SubjectInstance)
MATCH (si)-[:INSTANCE_OF]->(su:Subject)
MATCH (si)-[:OFFERED_IN]->(ac:AcademicCycle)
OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
RETURN
  g.id AS group_id,
  su.code AS course_code,
  su.name AS course_name,
  gt.g_type AS g_type,
  g.number AS group_num,
  g.weekday AS weekday,
  g.start_hr AS start,
  g.end_time AS end,
  g.pnp AS pnp,
  ac.year AS cycle_year,
  ac.season AS cycle_season,
  r.building AS building,
  r.room_num AS room_num
ORDER BY ac.year DESC, ac.season, su.name, gt.g_type, g.number
"""


def _cycle(year, season) -> str:
    if year and season:
        return f"{year} {season}"
    return ""


def _room(building, room_num) -> str:
    if building and room_num:
        return f"{building} {room_num}"
    return building or ""


async def teacher_groups(session: AsyncSession, idx: str) -> list[TeachingGroupItem]:
    rows = await run(session, _TEACHER_GROUPS, idx=idx)
    return [
        TeachingGroupItem(
            group_id=row["group_id"],
            course_code=row["course_code"] or "",
            course_name=row["course_name"] or "",
            g_type=row["g_type"],
            group_num=row["group_num"],
            academic_cycle=_cycle(row.get("cycle_year"), row.get("cycle_season")),
            room=_room(row.get("building"), row.get("room_num")),
            weekday=row.get("weekday") if row.get("weekday") is not None else 0,
            start=row.get("start"),
            end=row.get("end"),
            pnp=row.get("pnp") or "",
        )
        for row in rows
    ]
