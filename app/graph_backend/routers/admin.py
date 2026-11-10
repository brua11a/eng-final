from datetime import datetime, time

from fastapi import APIRouter, Depends
from neo4j import AsyncSession
from neo4j.exceptions import ConstraintError, Neo4jError

from app.database import get_session
from app.graph_backend.auth import hash_password, require, roles_from_flags
from app.graph_backend.query import next_id, one, run, tx_one
from app.schemas.academic_cycle import (
    AcademicCycleCreateRequest,
    AcademicCycleCreateResponse,
    AcademicCycleListResponse,
    MyAcademicCycleItem,
)
from app.schemas.admin_lists import (
    AdminCurriculumItem,
    AdminCurriculumListResponse,
    AdminGroupItem,
    AdminGroupListResponse,
    AdminStudentItem,
    AdminStudentListResponse,
    AdminTeacherItem,
    AdminTeacherListResponse,
    AdminTermItem,
    AdminTermListResponse,
    AdminTurnItem,
    AdminTurnListResponse,
    SubjectListItem,
    SubjectListResponse,
)
from app.schemas.admin_links import (
    AdminCreateRequest,
    AdminCreateResponse,
    AssignTurnRequest,
    AssignTurnResponse,
    DeanRegisterRequest,
    DeanRegisterResponse,
    EnrolStudentRequest,
    EnrolStudentResponse,
    NextIdxResponse,
    ProgrammeCreateRequest,
    ProgrammeCreateResponse,
    TermSubjectRequest,
    TermSubjectResponse,
)
from app.schemas.auth import (
    AddRoleRequest,
    AddRoleResponse,
    AssignUserRequest,
    AssignUserResponse,
    RemoveRoleRequest,
    RemoveRoleResponse,
    UserAccountResponse,
    UserIdxRequest,
)
from app.schemas.curriculum import (
    CurriculumCreateRequest,
    CurriculumCreateResponse,
    ProgrammeItem,
    ProgrammeListResponse,
)
from app.schemas.curriculum_term import CurriculumTermCreateRequest, CurriculumTermCreateResponse
from app.schemas.faculty import FacultyCreateRequest, FacultyCreateResponse
from app.schemas.group import (
    GroupCreateRequest,
    GroupCreateResponse,
    GroupTypeCreateRequest,
    GroupTypeCreateResponse,
    TeacherAssignRequest,
    TeacherAssignResponse,
)
from app.schemas.registration import StartRegistrationsRequest, StartRegistrationsResponse
from app.schemas.room import RoomCreateRequest, RoomCreateResponse, RoomItem, RoomListResponse
from app.schemas.student import StudentCreateRequest, StudentCreateResponse
from app.schemas.subject import SubjectCreateRequest, SubjectCreateResponse
from app.schemas.teacher import TeacherCreateRequest, TeacherCreateResponse

from app.graph_backend.errors import db_err

router = APIRouter(prefix="/admin", tags=["admin"])
_admin = require("Admin")


def _zoned_time(value: time) -> str:
    text = value.isoformat()
    return text if value.tzinfo else f"{text}+01:00"


def _zoned_datetime(value: datetime) -> str:
    text = value.isoformat()
    return text if value.tzinfo else f"{text}+01:00"


def _idx_taken(exc: Neo4jError) -> bool:
    """True when a CREATE failed because another person already has this idx."""
    return isinstance(exc, ConstraintError) and "`idx`" in (exc.message or "")


@router.post("/teachers", response_model=TeacherCreateResponse)
async def create_teacher(
    body: TeacherCreateRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> TeacherCreateResponse:
    idx = body.idx
    try:
        row = await one(
            session,
            """
            MATCH (f:Faculty {id: $faculty_id})
            CREATE (t:Teacher:Person {
              idx: $idx,
              name: $name,
              surname: $surname,
              phone: $phone,
              degree: $degree,
              working_since: date($working_since),
              photo: $photo
            })
            CREATE (t)-[:WORKS_AT]->(f)
            RETURN
              t.idx AS idx, t.name AS name, t.surname AS surname, t.phone AS phone,
              t.degree AS degree, t.photo AS photo, t.working_since AS working_since,
              f.id AS faculty_id
            """,
            faculty_id=body.faculty_id,
            idx=idx,
            name=body.name,
            surname=body.surname,
            phone=body.phone,
            degree=body.degree,
            working_since=body.working_since.isoformat(),
            photo=body.photo,
        )
    except Neo4jError as exc:
        return TeacherCreateResponse(
            idx=idx, name=body.name, surname=body.surname, phone=body.phone,
            degree=body.degree, photo=body.photo, working_since=body.working_since,
            faculty_id=body.faculty_id,
            err=f"Person with idx {idx} already exists" if _idx_taken(exc) else db_err(exc),
        )
    if row is None:
        return TeacherCreateResponse(
            idx=idx, name=body.name, surname=body.surname, phone=body.phone,
            degree=body.degree, photo=body.photo, working_since=body.working_since,
            faculty_id=body.faculty_id, err="Faculty not found",
        )
    return TeacherCreateResponse(**row)


@router.post("/students", response_model=StudentCreateResponse)
async def create_student(
    body: StudentCreateRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> StudentCreateResponse:
    idx = body.idx

    def failed(err: str) -> StudentCreateResponse:
        return StudentCreateResponse(
            idx=idx, name=body.name, surname=body.surname, phone=body.phone,
            photo=body.photo, joined=body.joined, err=err,
        )

    try:
        programme = await one(
            session,
            """
            MATCH (p:Programme {id: $programme})
            RETURN
              COUNT { (p)-[:HAS_CURRICULUM]->(:Curriculum) } AS curricula,
              COLLECT {
                MATCH (p)-[:HAS_CURRICULUM]->(c:Curriculum)-[:HAS_TERM]->(ct:CurriculumTerm)
                WHERE ($term_id IS NULL AND ct.sem = 1) OR ct.id = $term_id
                RETURN ct.id ORDER BY c.intake_year DESC
              } AS terms
            """,
            programme=body.programme,
            term_id=body.term_id,
        )
        if programme is None:
            return failed("Programme not found")
        if programme["curricula"] == 0:
            return failed("Programme has no curriculum")
        if not programme["terms"]:
            if body.term_id:
                return failed("Term does not belong to this programme")
            return failed("Programme has no first semester")
        row = await one(
            session,
            """
            MATCH (ct:CurriculumTerm {id: $term_id})
            CREATE (st:Student:Person {
              idx: $idx, name: $name, surname: $surname, phone: $phone,
              joined: datetime($joined), photo: $photo
            })
            CREATE (st)-[:ENROLLED]->(ct)
            RETURN st.idx AS idx, st.name AS name, st.surname AS surname,
                   st.phone AS phone, st.photo AS photo, st.joined AS joined
            """,
            term_id=programme["terms"][0],
            idx=idx,
            name=body.name,
            surname=body.surname,
            phone=body.phone,
            joined=_zoned_datetime(body.joined),
            photo=body.photo,
        )
    except Neo4jError as exc:
        return failed(f"Person with idx {idx} already exists" if _idx_taken(exc) else db_err(exc))
    if row is None:
        return failed("Term not found")
    return StudentCreateResponse(**row)


@router.post("/users", response_model=AssignUserResponse)
async def assign_user(
    body: AssignUserRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> AssignUserResponse:
    try:
        row = await one(
            session,
            """
            MATCH (owner:Person {idx: $idx})
            SET owner:User, owner.email = $email, owner.passwd_hash = $passwd_hash
            RETURN owner.email AS email,
              owner.idx AS idx,
              owner:Admin AS admin,
              owner:Teacher AS teacher,
              owner:Student AS student
            """,
            idx=body.idx,
            email=body.email,
            passwd_hash=hash_password(body.passwd),
        )
    except Neo4jError as exc:
        return AssignUserResponse(email=body.email, idx=body.idx, err=db_err(exc))
    if row is None:
        return AssignUserResponse(email=body.email, idx=body.idx, err="Account not found")
    return AssignUserResponse(
        email=row["email"],
        idx=row["idx"],
        roles=list(roles_from_flags(row["admin"], row["teacher"], row["student"])),
    )


@router.post("/users/deactivate", response_model=UserAccountResponse)
async def deactivate_user(
    body: UserIdxRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> UserAccountResponse:
    try:
        row = await one(
            session,
            """
            MATCH (u:User {idx: $idx})
            SET u:Inactive, u.deactivated_at = datetime()
            RETURN u.idx AS idx
            """,
            idx=body.idx,
        )
    except Neo4jError as exc:
        return UserAccountResponse(idx=body.idx, err=db_err(exc))
    if row is None:
        return UserAccountResponse(idx=body.idx, err="Account not found")
    return UserAccountResponse(**row)


@router.post("/users/activate", response_model=UserAccountResponse)
async def activate_user(
    body: UserIdxRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> UserAccountResponse:
    try:
        row = await one(
            session,
            """
            MATCH (u:User {idx: $idx})
            REMOVE u:Inactive, u.deactivated_at
            RETURN u.idx AS idx
            """,
            idx=body.idx,
        )
    except Neo4jError as exc:
        return UserAccountResponse(idx=body.idx, err=db_err(exc))
    if row is None:
        return UserAccountResponse(idx=body.idx, err="Account not found")
    return UserAccountResponse(**row)


_ROLE_STATE = """
MATCH (p:Person {idx: $idx})
RETURN p:Admin AS admin, p:Teacher AS teacher, p:Student AS student, p.email AS email
"""

_ADD_ROLE = {
    "Admin": """
        MATCH (p:Person {idx: $idx})
        SET p:Admin
        RETURN p.idx AS idx, p.email AS email, p:Admin AS admin, p:Teacher AS teacher, p:Student AS student
    """,
    "Teacher": """
        MATCH (p:Person {idx: $idx})
        SET p:Teacher, p.degree = $degree, p.working_since = date($working_since)
        RETURN p.idx AS idx, p.email AS email, p:Admin AS admin, p:Teacher AS teacher, p:Student AS student
    """,
    "Student": """
        MATCH (p:Person {idx: $idx})
        SET p:Student, p.joined = datetime($joined)
        RETURN p.idx AS idx, p.email AS email, p:Admin AS admin, p:Teacher AS teacher, p:Student AS student
    """,
}


# Runs in the same transaction after _LOCK_PERSON. Labels are read by a new statement, so
# they reflect the state after the lock was acquired (a single statement would see labels
# as they were when it matched the node, before waiting for the lock).
_LOCK_PERSON = "MATCH (p:Person {idx: $idx}) SET p.idx = p.idx RETURN p.idx AS idx"

_REMOVE_ROLE = {
    role: f"""
        MATCH (p:Person {{idx: $idx}})
        // labels(p) rather than p:Label: after waiting for the lock, the label predicate
        // could still report a label that the other transaction has just removed.
        WITH p, labels(p) AS l
        WITH p, "Admin" IN l AS admin, "Teacher" IN l AS teacher, "Student" IN l AS student,
             "{role}" IN l AND size([r IN ["Admin", "Teacher", "Student"] WHERE r IN l]) > 1 AS removed
        FOREACH (_ IN CASE WHEN removed THEN [1] ELSE [] END | REMOVE p:{role})
        // Flags are read before REMOVE; the caller derives the resulting roles from them.
        RETURN p.idx AS idx, p.email AS email, admin, teacher, student, removed
    """
    for role in ("Admin", "Teacher", "Student")
}


@router.post("/users/roles", response_model=AddRoleResponse)
async def add_role(
    body: AddRoleRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> AddRoleResponse:
    try:
        current = await one(session, _ROLE_STATE, idx=body.idx)
    except Neo4jError as exc:
        return AddRoleResponse(idx=body.idx, err=db_err(exc))
    if current is None:
        return AddRoleResponse(idx=body.idx, err="Person not found")
    if current[body.role.lower()]:
        return AddRoleResponse(
            idx=body.idx,
            roles=list(roles_from_flags(current["admin"], current["teacher"], current["student"])),
            err="Role already assigned",
        )
    params: dict = {"idx": body.idx}
    if body.role == "Teacher":
        if not body.degree or body.working_since is None:
            return AddRoleResponse(idx=body.idx, err="degree and working_since are required")
        params["degree"] = body.degree
        params["working_since"] = body.working_since.isoformat()
    elif body.role == "Student":
        if body.joined is None:
            return AddRoleResponse(idx=body.idx, err="joined is required")
        params["joined"] = _zoned_datetime(body.joined)
    try:
        row = await one(session, _ADD_ROLE[body.role], **params)
    except Neo4jError as exc:
        return AddRoleResponse(idx=body.idx, err=db_err(exc))
    if row is None:
        return AddRoleResponse(idx=body.idx, err="Person not found")
    return AddRoleResponse(
        idx=row["idx"],
        email=row["email"],
        roles=list(roles_from_flags(row["admin"], row["teacher"], row["student"])),
    )


@router.post("/users/roles/remove", response_model=RemoveRoleResponse)
async def remove_role(
    body: RemoveRoleRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> RemoveRoleResponse:
    try:
        current = await one(session, _ROLE_STATE, idx=body.idx)
    except Neo4jError as exc:
        return RemoveRoleResponse(idx=body.idx, err=db_err(exc))
    if current is None:
        return RemoveRoleResponse(idx=body.idx, err="Person not found")
    if not current[body.role.lower()]:
        return RemoveRoleResponse(
            idx=body.idx,
            roles=list(roles_from_flags(current["admin"], current["teacher"], current["student"])),
            err="Role not assigned",
        )
    remaining = sum(
        1
        for key in ("admin", "teacher", "student")
        if current[key] and key != body.role.lower()
    )
    if remaining == 0:
        return RemoveRoleResponse(
            idx=body.idx,
            roles=list(roles_from_flags(current["admin"], current["teacher"], current["student"])),
            err="Cannot remove last role",
        )
    try:
        tx = await session.begin_transaction()
        try:
            row = None
            if await tx_one(tx, _LOCK_PERSON, idx=body.idx) is not None:
                row = await tx_one(tx, _REMOVE_ROLE[body.role], idx=body.idx)
            await tx.commit()
        finally:
            await tx.close()
    except Neo4jError as exc:
        return RemoveRoleResponse(idx=body.idx, err=db_err(exc))
    if row is None:
        return RemoveRoleResponse(idx=body.idx, err="Person not found")
    flags = {key: row[key] for key in ("admin", "teacher", "student")}
    if not row["removed"]:
        return RemoveRoleResponse(
            idx=row["idx"],
            email=row["email"],
            roles=list(roles_from_flags(**flags)),
            err="Cannot remove last role",
        )
    flags[body.role.lower()] = False
    return RemoveRoleResponse(idx=row["idx"], email=row["email"], roles=list(roles_from_flags(**flags)))


@router.post("/group-types", response_model=GroupTypeCreateResponse)
async def create_group_type(
    body: GroupTypeCreateRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> GroupTypeCreateResponse:
    type_id = await next_id(session, "GroupType")
    instance_id = await next_id(session, "SubjectInstance")

    def failed(err: str, id: str = type_id) -> GroupTypeCreateResponse:
        return GroupTypeCreateResponse(
            id=id, subject_code=body.subject_code, cycle_id=body.cycle_id,
            g_type=body.g_type, weight=body.weight, err=err,
        )

    try:
        existing = await one(
            session,
            """
            MATCH (:Subject {code: $subject_code})<-[:INSTANCE_OF]-(si:SubjectInstance)-[:OFFERED_IN]->(:AcademicCycle {id: $cycle_id})
            MATCH (si)-[:HAS_TYPE]->(gt:GroupType {g_type: $g_type})
            RETURN gt.id AS id
            """,
            subject_code=body.subject_code,
            cycle_id=body.cycle_id,
            g_type=body.g_type,
        )
        if existing is not None:
            return failed("Group type already exists", existing["id"])
        row = await one(
            session,
            """
            MATCH (su:Subject {code: $subject_code})
            MATCH (ac:AcademicCycle {id: $cycle_id})
            WHERE EXISTS { (su)<-[:INCLUDES]-(:CurriculumTerm)-[:TAUGHT_IN]->(ac) }
            // Write lock on the subject: concurrent requests for it wait here, so neither
            // the subject instance nor the group type can be created twice.
            SET su.code = su.code
            MERGE (su)<-[:INSTANCE_OF]-(si:SubjectInstance)-[:OFFERED_IN]->(ac)
              ON CREATE SET si.id = $instance_id
            WITH su, ac, si
            OPTIONAL MATCH (si)-[:HAS_TYPE]->(old:GroupType {g_type: $g_type})
            FOREACH (_ IN CASE WHEN old IS NULL THEN [1] ELSE [] END |
              CREATE (si)-[:HAS_TYPE]->(:GroupType {id: $id, g_type: $g_type, weight: $weight})
            )
            WITH su, ac, si, old IS NOT NULL AS existed
            MATCH (si)-[:HAS_TYPE]->(gt:GroupType {g_type: $g_type})
            RETURN gt.id AS id, su.code AS subject_code, ac.id AS cycle_id,
                   gt.g_type AS g_type, gt.weight AS weight, existed
            """,
            subject_code=body.subject_code,
            cycle_id=body.cycle_id,
            instance_id=instance_id,
            id=type_id,
            g_type=body.g_type,
            weight=body.weight,
        )
    except Neo4jError as exc:
        return failed(db_err(exc))
    if row is None:
        return failed("Subject or cycle not found, or subject is not taught in this cycle")
    if row.pop("existed"):
        return failed("Group type already exists", row["id"])
    return GroupTypeCreateResponse(**row)


@router.post("/groups", response_model=GroupCreateResponse)
async def create_group(
    body: GroupCreateRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> GroupCreateResponse:
    group_id = await next_id(session, "Group")
    try:
        row = await one(
            session,
            """
            MATCH (su:Subject {code: $subject_code})<-[:INSTANCE_OF]-(si:SubjectInstance)-[:OFFERED_IN]->(ac:AcademicCycle {id: $cycle_id})
            MATCH (si)-[:HAS_TYPE]->(gt:GroupType {g_type: $g_type})
            MATCH (r:Room {id: $room_id})
            CREATE (g:Group {
              id: $id, weekday: $weekday, number: $number, pnp: $pnp,
              capacity: $capacity, start_hr: time($start_hr), end_time: time($end_time)
            })-[:OF_TYPE]->(gt),
            (g)-[:IN_ROOM]->(r)
            RETURN g.id AS id, g.weekday AS weekday, gt.g_type AS g_type, g.number AS number,
                   g.pnp AS pnp, g.capacity AS capacity, g.start_hr AS start_hr, g.end_time AS end_time,
                   su.code AS subject_code, ac.id AS cycle_id, r.id AS room_id
            """,
            subject_code=body.subject_code,
            cycle_id=body.cycle_id,
            room_id=body.room_id,
            id=group_id,
            weekday=body.weekday,
            g_type=body.g_type,
            number=body.number,
            pnp=body.pnp,
            capacity=body.capacity,
            start_hr=_zoned_time(body.start_hr),
            end_time=_zoned_time(body.end_time),
        )
    except Neo4jError as exc:
        return GroupCreateResponse(
            id=group_id, weekday=body.weekday, g_type=body.g_type, number=body.number,
            pnp=body.pnp, capacity=body.capacity, start_hr=body.start_hr, end_time=body.end_time,
            subject_code=body.subject_code, cycle_id=body.cycle_id, room_id=body.room_id,
            err=db_err(exc),
        )
    if row is None:
        return GroupCreateResponse(
            id=group_id, weekday=body.weekday, g_type=body.g_type, number=body.number,
            pnp=body.pnp, capacity=body.capacity, start_hr=body.start_hr, end_time=body.end_time,
            subject_code=body.subject_code, cycle_id=body.cycle_id, room_id=body.room_id,
            err="Room not found, or this subject has no such group type in this cycle",
        )
    return GroupCreateResponse(**row)


@router.post("/groups/teachers", response_model=TeacherAssignResponse)
async def assign_teacher_to_group(
    body: TeacherAssignRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> TeacherAssignResponse:
    try:
        row = await one(
            session,
            """
            MATCH (t:Teacher {idx: $teacher_idx})
            MATCH (g:Group {id: $group_id})
            SET g.id = g.id
            MERGE (t)-[:TEACHES]->(g)
            RETURN t.idx AS teacher_idx, g.id AS group_id
            """,
            teacher_idx=body.teacher_idx,
            group_id=body.group_id,
        )
    except Neo4jError as exc:
        return TeacherAssignResponse(
            teacher_idx=body.teacher_idx,
            group_id=body.group_id,
            err=db_err(exc),
        )
    if row is None:
        return TeacherAssignResponse(
            teacher_idx=body.teacher_idx,
            group_id=body.group_id,
            err="Teacher or group not found",
        )
    return TeacherAssignResponse(**row)


@router.post("/rooms", response_model=RoomCreateResponse)
async def create_room(
    body: RoomCreateRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> RoomCreateResponse:
    room_id = await next_id(session, "Room")
    try:
        row = await one(
            session,
            """
            CREATE (r:Room {id: $id, building: $building, room_num: $room_num})
            RETURN r.id AS id, r.building AS building, r.room_num AS room_num
            """,
            id=room_id,
            building=body.building,
            room_num=body.room_num,
        )
    except Neo4jError as exc:
        return RoomCreateResponse(
            id=room_id,
            building=body.building,
            room_num=body.room_num,
            err=db_err(exc),
        )
    return RoomCreateResponse(**row)


@router.post("/academic-cycles", response_model=AcademicCycleCreateResponse)
async def create_cycle(
    body: AcademicCycleCreateRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> AcademicCycleCreateResponse:
    cycle_id = await next_id(session, "AcademicCycle")
    if body.end_date <= body.start_date:
        return AcademicCycleCreateResponse(
            id=cycle_id, **body.model_dump(), err="end_date must be after start_date"
        )
    try:
        row = await one(
            session,
            """
            CREATE (ac:AcademicCycle {
              id: $id, year: $year, season: $season,
              start_date: date($start_date), end_date: date($end_date)
            })
            RETURN ac.id AS id, ac.year AS year, ac.season AS season,
                   ac.start_date AS start_date, ac.end_date AS end_date
            """,
            id=cycle_id,
            year=body.year,
            season=body.season,
            start_date=body.start_date.isoformat(),
            end_date=body.end_date.isoformat(),
        )
    except Neo4jError as exc:
        return AcademicCycleCreateResponse(id=cycle_id, **body.model_dump(), err=db_err(exc))
    return AcademicCycleCreateResponse(**row)


@router.post("/subjects", response_model=SubjectCreateResponse)
async def create_subject(
    body: SubjectCreateRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> SubjectCreateResponse:
    try:
        row = await one(
            session,
            """
            MERGE (su:Subject {code: $code})
            SET su.name = $name, su.ects = $ects
            RETURN su.code AS code, su.name AS name, su.ects AS ects
            """,
            code=body.code,
            name=body.name,
            ects=body.ects,
        )
    except Neo4jError as exc:
        return SubjectCreateResponse(code=body.code, name=body.name, ects=body.ects, err=db_err(exc))
    return SubjectCreateResponse(**row)


@router.post("/curriculum-terms", response_model=CurriculumTermCreateResponse)
async def create_term(
    body: CurriculumTermCreateRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> CurriculumTermCreateResponse:
    term_id = await next_id(session, "CurriculumTerm")
    if body.cycle_id is None:
        return CurriculumTermCreateResponse(
            id=term_id, sem=body.sem, curriculum_id=body.curriculum_id, err="cycle_id is required",
        )
    try:
        row = await one(
            session,
            """
            MATCH (c:Curriculum {id: $curriculum_id})
            MATCH (ac:AcademicCycle {id: $cycle_id})
            CREATE (ct:CurriculumTerm {id: $id, sem: $sem})
            CREATE (c)-[:HAS_TERM]->(ct)
            CREATE (ct)-[:TAUGHT_IN]->(ac)
            RETURN ct.id AS id, ct.sem AS sem, c.id AS curriculum_id, ac.id AS cycle_id
            """,
            curriculum_id=body.curriculum_id,
            cycle_id=body.cycle_id,
            id=term_id,
            sem=body.sem,
        )
    except Neo4jError as exc:
        return CurriculumTermCreateResponse(
            id=term_id, sem=body.sem, curriculum_id=body.curriculum_id,
            cycle_id=body.cycle_id, err=db_err(exc),
        )
    if row is None:
        return CurriculumTermCreateResponse(
            id=term_id, sem=body.sem, curriculum_id=body.curriculum_id,
            cycle_id=body.cycle_id, err="Curriculum or cycle not found",
        )
    return CurriculumTermCreateResponse(**row)


@router.post("/curricula", response_model=CurriculumCreateResponse)
async def create_curriculum(
    body: CurriculumCreateRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> CurriculumCreateResponse:
    curriculum_id = await next_id(session, "Curriculum")
    try:
        row = await one(
            session,
            """
            MATCH (p:Programme {id: $programme_id})
            CREATE (c:Curriculum {id: $id, intake_year: $intake_year})
            CREATE (p)-[:HAS_CURRICULUM]->(c)
            RETURN c.id AS id, p.id AS programme_id, c.intake_year AS intake_year
            """,
            programme_id=body.programme_id,
            id=curriculum_id,
            intake_year=body.intake_year,
        )
    except Neo4jError as exc:
        return CurriculumCreateResponse(
            id=curriculum_id, programme_id=body.programme_id, intake_year=body.intake_year,
            err=db_err(exc),
        )
    if row is None:
        return CurriculumCreateResponse(
            id=curriculum_id, programme_id=body.programme_id, intake_year=body.intake_year,
            err="Programme not found",
        )
    return CurriculumCreateResponse(**row)


@router.post("/faculties", response_model=FacultyCreateResponse)
async def create_faculty(
    body: FacultyCreateRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> FacultyCreateResponse:
    faculty_id = await next_id(session, "Faculty")
    try:
        row = await one(
            session,
            """
            CREATE (fa:Faculty {id: $id, name: $name, full_name: $full_name})
            RETURN fa.id AS id, fa.name AS name, fa.full_name AS full_name
            """,
            id=faculty_id,
            name=body.name,
            full_name=body.full_name,
        )
    except Neo4jError as exc:
        return FacultyCreateResponse(
            id=faculty_id, name=body.name, full_name=body.full_name, err=db_err(exc),
        )
    return FacultyCreateResponse(**row)


@router.post("/registrations", response_model=StartRegistrationsResponse)
async def start_registrations(
    body: StartRegistrationsRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> StartRegistrationsResponse:
    registration_id = await next_id(session, "Registration")
    begun = session.begin_transaction()
    tx = await begun if hasattr(begun, "__await__") else begun
    try:
        created = await tx_one(
            tx,
            """
            MATCH (ac:AcademicCycle {id: $cycle_id})
            MATCH (fa:Faculty {id: $faculty_id})
            CREATE (reg:Registration {id: $id, name: $name, reg_type: $reg_type})
            CREATE (reg)-[:FOR_CYCLE]->(ac)
            CREATE (reg)-[:FOR_FACULTY]->(fa)
            RETURN reg.id AS id
            """,
            cycle_id=body.cycle_id,
            faculty_id=body.faculty_id,
            id=registration_id,
            name=body.name,
            reg_type=body.reg_type,
        )
        if created is None:
            await tx.rollback()
            return StartRegistrationsResponse(err="Cycle or faculty not found")
        turns = [
            {
                "id": await next_id(session, "RegistrationTurn"),
                "turn_number": turn.turn_number,
                "date": turn.date.isoformat(),
                "start": _zoned_time(turn.start),
                "end": _zoned_time(turn.end),
            }
            for turn in body.turns
        ]
        written = await tx_one(
            tx,
            """
            MATCH (reg:Registration {id: $registration_id})
            UNWIND $turns AS turn
            CREATE (rt:RegistrationTurn {
              id: turn.id, turn_number: turn.turn_number, date: date(turn.date),
              start_hr: time(turn.start), end_time: time(turn.end)
            })
            CREATE (reg)-[:HAS_TURN]->(rt)
            RETURN count(rt) AS created
            """,
            registration_id=registration_id,
            turns=turns,
        )
        if written["created"] != len(turns):
            await tx.rollback()
            return StartRegistrationsResponse(err="Could not create the registration turns")
        opened = await tx_one(
            tx,
            """
            MATCH (reg:Registration {id: $registration_id})
            UNWIND $group_ids AS group_id
            MATCH (g:Group {id: group_id})
            MERGE (reg)-[:OPENS]->(g)
            RETURN collect(g.id) AS found
            """,
            registration_id=registration_id,
            group_ids=body.group_ids,
        )
        found = set(opened["found"])
        missing = [gid for gid in body.group_ids if gid not in found]
        if missing:
            await tx.rollback()
            return StartRegistrationsResponse(err=f"Groups not found: {', '.join(missing)}")
        await tx.commit()
    except Neo4jError as exc:
        await tx.rollback()
        return StartRegistrationsResponse(err=db_err(exc))
    finally:
        try:
            await tx.close()
        except Exception:
            pass
    return StartRegistrationsResponse(
        id=registration_id,
        name=body.name,
        reg_type=body.reg_type,
        turns=body.turns,
        group_ids=body.group_ids,
    )


@router.get("/programmes", response_model=ProgrammeListResponse)
async def list_programmes(
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> ProgrammeListResponse:
    rows = await run(
        session,
        """
        MATCH (p:Programme)-[:OFFERED_BY]->(fa:Faculty)
        RETURN p.id AS id, p.name AS name, fa.id AS faculty_id
        ORDER BY p.name
        """,
    )
    return ProgrammeListResponse(programmes=[ProgrammeItem(**row) for row in rows])


@router.get("/rooms", response_model=RoomListResponse)
async def list_rooms(
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> RoomListResponse:
    rows = await run(
        session,
        "MATCH (r:Room) RETURN r.id AS id, r.building AS building, r.room_num AS room_num ORDER BY r.building, r.room_num",
    )
    return RoomListResponse(rooms=[RoomItem(**row) for row in rows])


@router.get("/academic-cycles", response_model=AcademicCycleListResponse)
async def list_cycles(
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> AcademicCycleListResponse:
    rows = await run(
        session,
        "MATCH (ac:AcademicCycle) RETURN ac.id AS id, ac.year AS year, ac.season AS season, "
        "ac.start_date AS start_date, ac.end_date AS end_date ORDER BY ac.start_date",
    )
    return AcademicCycleListResponse(cycles=[MyAcademicCycleItem(**row) for row in rows])


@router.get("/subjects", response_model=SubjectListResponse)
async def list_subjects(
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> SubjectListResponse:
    rows = await run(
        session,
        "MATCH (su:Subject) RETURN su.code AS code, su.name AS name ORDER BY su.code",
    )
    return SubjectListResponse(subjects=[SubjectListItem(**row) for row in rows])


@router.get("/curricula", response_model=AdminCurriculumListResponse)
async def list_curricula(
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> AdminCurriculumListResponse:
    rows = await run(
        session,
        """
        MATCH (c:Curriculum)<-[:HAS_CURRICULUM]-(p:Programme)
        RETURN c.id AS id, p.name AS programme_name, c.intake_year AS intake_year
        ORDER BY p.name, c.intake_year DESC
        """,
    )
    return AdminCurriculumListResponse(curricula=[AdminCurriculumItem(**row) for row in rows])


@router.get("/teachers", response_model=AdminTeacherListResponse)
async def list_teachers(
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> AdminTeacherListResponse:
    rows = await run(
        session,
        """
        MATCH (t:Teacher)
        RETURN t.idx AS idx, t.name AS name, t.surname AS surname
        ORDER BY t.surname, t.name
        """,
    )
    return AdminTeacherListResponse(teachers=[AdminTeacherItem(**row) for row in rows])


_WEEKDAYS = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}


@router.get("/groups", response_model=AdminGroupListResponse)
async def list_groups(
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> AdminGroupListResponse:
    rows = await run(
        session,
        """
        MATCH (g:Group)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(si:SubjectInstance)
        MATCH (si)-[:INSTANCE_OF]->(su:Subject)
        MATCH (si)-[:OFFERED_IN]->(ac:AcademicCycle)
        RETURN
          g.id AS id,
          su.code AS course_code,
          ac.year + " " + ac.season AS cycle,
          gt.g_type AS g_type,
          su.name AS course_name,
          g.number AS number,
          g.weekday AS weekday,
          g.start_hr AS start,
          g.end_time AS end
        ORDER BY su.code, ac.year, ac.season, gt.g_type, g.number
        """,
    )
    groups = []
    for row in rows:
        day = _WEEKDAYS.get(row["weekday"], "?")
        hours = f"{row['start'].strftime('%H:%M')}-{row['end'].strftime('%H:%M')}"
        label = (
            f"{row['course_code']} {row['course_name']}, {row['cycle']}, "
            f"{row['g_type']} #{row['number']}, {day} {hours}"
        )
        groups.append(AdminGroupItem(id=row["id"], label=label))
    return AdminGroupListResponse(groups=groups)


@router.post("/admins", response_model=AdminCreateResponse)
async def create_admin(
    body: AdminCreateRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> AdminCreateResponse:
    try:
        row = await one(
            session,
            """
            CREATE (a:Admin:Person {idx: $idx, name: $name, surname: $surname, phone: $phone})
            RETURN a.idx AS idx, a.name AS name, a.surname AS surname, a.phone AS phone
            """,
            idx=body.idx,
            name=body.name,
            surname=body.surname,
            phone=body.phone,
        )
    except Neo4jError as exc:
        err = f"Person with idx {body.idx} already exists" if _idx_taken(exc) else db_err(exc)
        return AdminCreateResponse(**body.model_dump(), err=err)
    return AdminCreateResponse(**row)


@router.post("/users/remove", response_model=UserAccountResponse)
async def remove_user_account(
    body: UserIdxRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> UserAccountResponse:
    """Delete the login account; the person node and its history stay in the graph."""
    if body.idx == caller.idx:
        return UserAccountResponse(idx=body.idx, err="Cannot remove your own account")
    try:
        row = await one(
            session,
            """
            MATCH (u:User {idx: $idx})
            REMOVE u:User:Inactive, u.email, u.passwd_hash, u.deactivated_at
            RETURN u.idx AS idx
            """,
            idx=body.idx,
        )
    except Neo4jError as exc:
        return UserAccountResponse(idx=body.idx, err=db_err(exc))
    if row is None:
        return UserAccountResponse(idx=body.idx, err="Account not found")
    return UserAccountResponse(**row)


@router.post("/programmes", response_model=ProgrammeCreateResponse)
async def create_programme(
    body: ProgrammeCreateRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> ProgrammeCreateResponse:
    programme_id = await next_id(session, "Programme")
    try:
        row = await one(
            session,
            """
            MATCH (fa:Faculty {id: $faculty_id})
            CREATE (p:Programme {id: $id, name: $name})-[:OFFERED_BY]->(fa)
            RETURN p.id AS id, p.name AS name, fa.id AS faculty_id
            """,
            faculty_id=body.faculty_id,
            id=programme_id,
            name=body.name,
        )
    except Neo4jError as exc:
        return ProgrammeCreateResponse(**body.model_dump(), err=db_err(exc))
    if row is None:
        return ProgrammeCreateResponse(**body.model_dump(), err="Faculty not found")
    return ProgrammeCreateResponse(**row)


@router.post("/curriculum-terms/subjects", response_model=TermSubjectResponse)
async def add_subject_to_term(
    body: TermSubjectRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> TermSubjectResponse:
    try:
        row = await one(
            session,
            """
            MATCH (ct:CurriculumTerm {id: $term_id})
            MATCH (su:Subject {code: $subject_code})
            SET ct.id = ct.id
            WITH ct, su, EXISTS { (ct)-[:INCLUDES]->(su) } AS already
            MERGE (ct)-[:INCLUDES]->(su)
            RETURN already
            """,
            term_id=body.term_id,
            subject_code=body.subject_code,
        )
    except Neo4jError as exc:
        return TermSubjectResponse(**body.model_dump(), err=db_err(exc))
    if row is None:
        return TermSubjectResponse(**body.model_dump(), err="Term or subject not found")
    if row["already"]:
        return TermSubjectResponse(**body.model_dump(), err="Subject already in this term")
    return TermSubjectResponse(**body.model_dump())


@router.post("/students/enrol", response_model=EnrolStudentResponse)
async def enrol_student(
    body: EnrolStudentRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> EnrolStudentResponse:
    try:
        row = await one(
            session,
            """
            MATCH (st:Student {idx: $student_idx})
            MATCH (ct:CurriculumTerm {id: $term_id})
            SET st.idx = st.idx
            WITH st, ct, EXISTS { (st)-[:ENROLLED]->(ct) } AS already
            MERGE (st)-[:ENROLLED]->(ct)
            RETURN already
            """,
            student_idx=body.student_idx,
            term_id=body.term_id,
        )
    except Neo4jError as exc:
        return EnrolStudentResponse(**body.model_dump(), err=db_err(exc))
    if row is None:
        return EnrolStudentResponse(**body.model_dump(), err="Student or term not found")
    if row["already"]:
        return EnrolStudentResponse(**body.model_dump(), err="Student already enrolled in this term")
    return EnrolStudentResponse(**body.model_dump())


# All-or-nothing: checks and writes in one query. The write lock on the registration
# makes concurrent assignments to its turns wait, so a student cannot end up in two turns.
_ASSIGN_TURN = """
MATCH (rt:RegistrationTurn {id: $turn_id})<-[:HAS_TURN]-(reg:Registration)
SET reg.id = reg.id
WITH rt, reg
UNWIND $student_idxs AS sidx
OPTIONAL MATCH (st:Student {idx: sidx})
WITH rt, collect({
  idx: sidx,
  st: st,
  other: st IS NOT NULL AND EXISTS {
    MATCH (st)-[:ASSIGNED]->(o:RegistrationTurn)<-[:HAS_TURN]-(reg)
    WHERE o <> rt
  }
}) AS rows
WITH rt, rows,
  [r IN rows WHERE r.st IS NULL | r.idx] AS missing,
  [r IN rows WHERE r.other | r.idx] AS conflicts
WITH rt, rows, missing, conflicts, size(missing) = 0 AND size(conflicts) = 0 AS ok
FOREACH (r IN CASE WHEN ok THEN rows ELSE [] END |
  FOREACH (st IN [r.st] | MERGE (st)-[:ASSIGNED]->(rt))
)
RETURN missing, conflicts, CASE WHEN ok THEN [r IN rows | r.idx] ELSE [] END AS assigned
"""


@router.post("/registrations/turns/students", response_model=AssignTurnResponse)
async def assign_students_to_turn(
    body: AssignTurnRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> AssignTurnResponse:
    if not body.student_idxs:
        return AssignTurnResponse(turn_id=body.turn_id, err="No students given")
    try:
        row = await one(session, _ASSIGN_TURN, turn_id=body.turn_id, student_idxs=body.student_idxs)
    except Neo4jError as exc:
        return AssignTurnResponse(turn_id=body.turn_id, err=db_err(exc))
    if row is None:
        return AssignTurnResponse(turn_id=body.turn_id, err="Registration turn not found")
    if row["missing"]:
        return AssignTurnResponse(
            turn_id=body.turn_id, err=f"Students not found: {', '.join(row['missing'])}"
        )
    if row["conflicts"]:
        return AssignTurnResponse(
            turn_id=body.turn_id,
            err=f"Already assigned to another turn of this registration: {', '.join(row['conflicts'])}",
        )
    return AssignTurnResponse(turn_id=body.turn_id, assigned=row["assigned"])


@router.get("/students", response_model=AdminStudentListResponse)
async def list_students(
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> AdminStudentListResponse:
    rows = await run(
        session,
        """
        MATCH (st:Student)
        RETURN st.idx AS idx, st.name AS name, st.surname AS surname
        ORDER BY st.surname, st.name
        """,
    )
    return AdminStudentListResponse(students=[AdminStudentItem(**row) for row in rows])


@router.get("/curriculum-terms", response_model=AdminTermListResponse)
async def list_terms(
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> AdminTermListResponse:
    rows = await run(
        session,
        """
        MATCH (p:Programme)-[:HAS_CURRICULUM]->(c:Curriculum)-[:HAS_TERM]->(ct:CurriculumTerm)
        OPTIONAL MATCH (ct)-[:TAUGHT_IN]->(ac:AcademicCycle)
        RETURN ct.id AS id, p.name AS programme, c.intake_year AS intake_year, ct.sem AS sem,
               ac.year AS year, ac.season AS season
        ORDER BY p.name, c.intake_year DESC, ct.sem
        """,
    )
    terms = []
    for row in rows:
        cycle = f" ({row['year']} {row['season']})" if row["year"] else ""
        label = f"{row['programme']} {row['intake_year']}, sem. {row['sem']}{cycle}"
        terms.append(AdminTermItem(id=row["id"], label=label))
    return AdminTermListResponse(terms=terms)


@router.get("/registration-turns", response_model=AdminTurnListResponse)
async def list_turns(
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> AdminTurnListResponse:
    rows = await run(
        session,
        """
        MATCH (reg:Registration)-[:HAS_TURN]->(rt:RegistrationTurn)
        RETURN rt.id AS id, reg.name AS registration, rt.turn_number AS turn_number,
               rt.date AS date, rt.start_hr AS start, rt.end_time AS end
        ORDER BY rt.date DESC, reg.name, rt.turn_number
        """,
    )
    turns = []
    for row in rows:
        start = row["start"].strftime("%H:%M") if row["start"] else ""
        end = row["end"].strftime("%H:%M") if row["end"] else ""
        label = f"{row['registration']}, turn {row['turn_number']} ({row['date']} {start}-{end})"
        turns.append(AdminTurnItem(id=row["id"], label=label))
    return AdminTurnListResponse(turns=turns)


# Dean's office registration: bypasses registration turns, still allows only one group
# of each type per subject. Capacity is checked unless ignore_capacity is set.
# Locks the student, then the group, exactly like student registration (see student.py).
_DEAN_REGISTER = """
MATCH (st:Student {idx: $student_idx})
MATCH (g:Group {id: $group_id})-[:OF_TYPE]->(gt:GroupType)
SET st.idx = st.idx
SET g.capacity = g.capacity
WITH st, g,
  EXISTS { (st)-[:REGISTERED_IN]->(g) } AS already,
  EXISTS {
    MATCH (st)-[:REGISTERED_IN]->(other:Group)-[:OF_TYPE]->(gt)
    WHERE other <> g
  } AS conflict,
  COUNT { (g)<-[:REGISTERED_IN]-(:Student) } >= g.capacity AS full
WITH st, g, CASE
  WHEN already THEN "already"
  WHEN conflict THEN "conflict"
  WHEN full AND NOT $ignore_capacity THEN "full"
  ELSE "ok"
END AS status
FOREACH (_ IN CASE WHEN status = "ok" THEN [1] ELSE [] END |
  CREATE (st)-[:REGISTERED_IN {registered_at: datetime()}]->(g)
)
RETURN status
"""


@router.post("/groups/students", response_model=DeanRegisterResponse)
async def dean_register(
    body: DeanRegisterRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> DeanRegisterResponse:
    def result(err: str | None = None) -> DeanRegisterResponse:
        return DeanRegisterResponse(**body.model_dump(), err=err)

    try:
        row = await one(
            session,
            _DEAN_REGISTER,
            student_idx=body.student_idx,
            group_id=body.group_id,
            ignore_capacity=body.ignore_capacity,
        )
    except Neo4jError as exc:
        return result(db_err(exc))
    if row is None:
        return result("Student or group not found")
    errors = {
        "already": "Student is already registered in this group",
        "conflict": "Student is already registered in another group of this type for this subject",
        "full": "Group is full",
    }
    return result(errors.get(row["status"]))


# Suggestions only (max + 1 per idx format). Two admins may get the same suggestion;
# the idx KEY constraint then rejects the second create with a clear error.
_NEXT_IDX = """
RETURN
  coalesce(head(COLLECT {
    MATCH (p:Person) WHERE p.idx =~ 'T[0-9]+'
    RETURN toInteger(substring(p.idx, 1)) AS n ORDER BY n DESC LIMIT 1
  }), 0) + 1 AS teacher,
  coalesce(head(COLLECT {
    MATCH (p:Person) WHERE p.idx =~ '[0-9]+'
    RETURN toInteger(p.idx) AS n ORDER BY n DESC LIMIT 1
  }), 0) + 1 AS student,
  coalesce(head(COLLECT {
    MATCH (p:Person) WHERE p.idx =~ 'A[0-9]+'
    RETURN toInteger(substring(p.idx, 1)) AS n ORDER BY n DESC LIMIT 1
  }), 0) + 1 AS admin
"""


@router.get("/people/next-idx", response_model=NextIdxResponse)
async def next_person_idx(
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> NextIdxResponse:
    row = await one(session, _NEXT_IDX)
    return NextIdxResponse(
        teacher=f"T{row['teacher']:03d}",
        student=str(row["student"]),
        admin=f"A{row['admin']:03d}",
    )
