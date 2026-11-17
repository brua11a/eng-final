from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from neo4j import AsyncSession
from neo4j.exceptions import ConstraintError

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
    AssignUserRequest,
    AssignUserResponse,
    RolesResponse,
    UserAccountResponse,
    UserType,
    UserUpdateRequest,
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
from app.schemas.subject import SubjectCreateResponse, SubjectUpsertRequest
from app.schemas.teacher import TeacherCreateRequest, TeacherCreateResponse

from app.graph_backend.errors import conflict, db_err, invalid, not_found

router = APIRouter(prefix="/admin", tags=["admin"])
_admin = require("Admin")


def _zoned_time(value: time) -> str:
    text = value.isoformat()
    return text if value.tzinfo else f"{text}+01:00"


def _zoned_datetime(value: datetime) -> str:
    text = value.isoformat()
    return text if value.tzinfo else f"{text}+01:00"


def _idx_conflict(exc: ConstraintError, idx: str) -> HTTPException:
    """409 for a CREATE that failed because another person already has this idx."""
    if "`idx`" in (exc.message or ""):
        return conflict(f"Person with idx {idx} already exists")
    return conflict(db_err(exc))


def _location(request: Request, response: Response, route: str, **params: str) -> None:
    """Point the Location header of a 201 response at the GET endpoint of the new resource."""
    response.headers["Location"] = request.app.url_path_for(route, **params)


@router.post("/teachers", response_model=TeacherCreateResponse, status_code=201)
async def create_teacher(
    body: TeacherCreateRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> TeacherCreateResponse:
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
            idx=body.idx,
            name=body.name,
            surname=body.surname,
            phone=body.phone,
            degree=body.degree,
            working_since=body.working_since.isoformat(),
            photo=body.photo,
        )
    except ConstraintError as exc:
        raise _idx_conflict(exc, body.idx) from exc
    if row is None:
        raise not_found("Faculty")
    _location(request, response, "teacher_detail", idx=row["idx"])
    return TeacherCreateResponse(**row)


@router.post("/students", response_model=StudentCreateResponse, status_code=201)
async def create_student(
    body: StudentCreateRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> StudentCreateResponse:
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
        raise not_found("Programme")
    if programme["curricula"] == 0:
        raise conflict("Programme has no curriculum")
    if not programme["terms"]:
        if body.term_id:
            raise invalid("Term does not belong to this programme")
        raise conflict("Programme has no first semester")
    try:
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
            idx=body.idx,
            name=body.name,
            surname=body.surname,
            phone=body.phone,
            joined=_zoned_datetime(body.joined),
            photo=body.photo,
        )
    except ConstraintError as exc:
        raise _idx_conflict(exc, body.idx) from exc
    if row is None:
        raise not_found("Term")
    _location(request, response, "student_detail", student_idx=row["idx"])
    return StudentCreateResponse(**row)


@router.post("/users", response_model=AssignUserResponse, status_code=201)
async def assign_user(
    body: AssignUserRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> AssignUserResponse:
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
    if row is None:
        raise not_found("Person")
    return AssignUserResponse(
        email=row["email"],
        idx=row["idx"],
        roles=list(roles_from_flags(row["admin"], row["teacher"], row["student"])),
    )


@router.patch("/users/{idx}", response_model=UserAccountResponse)
async def update_user(
    idx: str,
    body: UserUpdateRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> UserAccountResponse:
    """Deactivates (`active: false`) or reactivates (`active: true`) a login account."""
    row = await one(
        session,
        _ACTIVATE if body.active else _DEACTIVATE,
        idx=idx,
    )
    if row is None:
        raise not_found("Account")
    return UserAccountResponse(idx=row["idx"], active=body.active)


_DEACTIVATE = """
MATCH (u:User {idx: $idx})
SET u:Inactive, u.deactivated_at = datetime()
RETURN u.idx AS idx
"""

_ACTIVATE = """
MATCH (u:User {idx: $idx})
REMOVE u:Inactive, u.deactivated_at
RETURN u.idx AS idx
"""


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


# PUT is idempotent: adding a role the person already has changes nothing and succeeds.
@router.put("/users/{idx}/roles/{role}", response_model=RolesResponse)
async def add_role(
    idx: str,
    role: UserType,
    body: AddRoleRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> RolesResponse:
    current = await one(session, _ROLE_STATE, idx=idx)
    if current is None:
        raise not_found("Person")
    if current[role.lower()]:
        return RolesResponse(
            idx=idx,
            email=current["email"],
            roles=list(roles_from_flags(current["admin"], current["teacher"], current["student"])),
        )
    params: dict = {"idx": idx}
    if role == "Teacher":
        if not body.degree or body.working_since is None:
            raise invalid("degree and working_since are required")
        params["degree"] = body.degree
        params["working_since"] = body.working_since.isoformat()
    elif role == "Student":
        if body.joined is None:
            raise invalid("joined is required")
        params["joined"] = _zoned_datetime(body.joined)
    row = await one(session, _ADD_ROLE[role], **params)
    if row is None:
        raise not_found("Person")
    return RolesResponse(
        idx=row["idx"],
        email=row["email"],
        roles=list(roles_from_flags(row["admin"], row["teacher"], row["student"])),
    )


@router.delete("/users/{idx}/roles/{role}", response_model=RolesResponse)
async def remove_role(
    idx: str,
    role: UserType,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> RolesResponse:
    current = await one(session, _ROLE_STATE, idx=idx)
    if current is None:
        raise not_found("Person")
    if not current[role.lower()]:
        raise not_found("Role")
    remaining = sum(
        1
        for key in ("admin", "teacher", "student")
        if current[key] and key != role.lower()
    )
    if remaining == 0:
        raise conflict("Cannot remove last role")
    tx = await session.begin_transaction()
    try:
        row = None
        if await tx_one(tx, _LOCK_PERSON, idx=idx) is not None:
            row = await tx_one(tx, _REMOVE_ROLE[role], idx=idx)
        await tx.commit()
    finally:
        await tx.close()
    if row is None:
        raise not_found("Person")
    if not row["removed"]:
        raise conflict("Cannot remove last role")
    flags = {key: row[key] for key in ("admin", "teacher", "student")}
    flags[role.lower()] = False
    return RolesResponse(idx=row["idx"], email=row["email"], roles=list(roles_from_flags(**flags)))


@router.post("/group-types", response_model=GroupTypeCreateResponse, status_code=201)
async def create_group_type(
    body: GroupTypeCreateRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> GroupTypeCreateResponse:
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
        raise conflict("Group type already exists")
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
        id=await next_id(session, "GroupType"),
        g_type=body.g_type,
        weight=body.weight,
    )
    if row is None:
        raise not_found("Subject taught in this cycle")
    if row.pop("existed"):
        raise conflict("Group type already exists")
    return GroupTypeCreateResponse(**row)


@router.post("/groups", response_model=GroupCreateResponse, status_code=201)
async def create_group(
    body: GroupCreateRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> GroupCreateResponse:
    row = await one(
        session,
        """
        MATCH (su:Subject {code: $subject_code})<-[:INSTANCE_OF]-(si:SubjectInstance)-[:OFFERED_IN]->(ac:AcademicCycle {id: $cycle_id})
        MATCH (si)-[:HAS_TYPE]->(gt:GroupType {g_type: $g_type})
        MATCH (r:Room {id: $room_id})
        CREATE (g:Group {
          id: $id, weekday: $weekday, number: $number, pnp: $pnp,
          capacity: $capacity, start_time: time($start_time), end_time: time($end_time)
        })-[:OF_TYPE]->(gt),
        (g)-[:IN_ROOM]->(r)
        RETURN g.id AS id, g.weekday AS weekday, gt.g_type AS g_type, g.number AS number,
               g.pnp AS pnp, g.capacity AS capacity, g.start_time AS start_time, g.end_time AS end_time,
               su.code AS subject_code, ac.id AS cycle_id, r.id AS room_id
        """,
        subject_code=body.subject_code,
        cycle_id=body.cycle_id,
        room_id=body.room_id,
        id=await next_id(session, "Group"),
        weekday=body.weekday,
        g_type=body.g_type,
        number=body.number,
        pnp=body.pnp,
        capacity=body.capacity,
        start_time=_zoned_time(body.start_time),
        end_time=_zoned_time(body.end_time),
    )
    if row is None:
        raise not_found("Room, or group type of this subject in this cycle,")
    _location(request, response, "group_detail", group_id=row["id"])
    return GroupCreateResponse(**row)


# Idempotent (MERGE): assigning a teacher who already teaches the group succeeds.
@router.post("/groups/teachers", response_model=TeacherAssignResponse)
async def assign_teacher_to_group(
    body: TeacherAssignRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> TeacherAssignResponse:
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
    if row is None:
        raise not_found("Teacher or group")
    return TeacherAssignResponse(**row)


@router.post("/rooms", response_model=RoomCreateResponse, status_code=201)
async def create_room(
    body: RoomCreateRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> RoomCreateResponse:
    row = await one(
        session,
        """
        CREATE (r:Room {id: $id, building: $building, room_num: $room_num})
        RETURN r.id AS id, r.building AS building, r.room_num AS room_num
        """,
        id=await next_id(session, "Room"),
        building=body.building,
        room_num=body.room_num,
    )
    return RoomCreateResponse(**row)


@router.post("/academic-cycles", response_model=AcademicCycleCreateResponse, status_code=201)
async def create_cycle(
    body: AcademicCycleCreateRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> AcademicCycleCreateResponse:
    if body.end_date <= body.start_date:
        raise invalid("end_date must be after start_date")
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
        id=await next_id(session, "AcademicCycle"),
        year=body.year,
        season=body.season,
        start_date=body.start_date.isoformat(),
        end_date=body.end_date.isoformat(),
    )
    return AcademicCycleCreateResponse(**row)


# The code identifies the subject, so it goes in the path. PUT creates the subject (201)
# or updates its name and ECTS (200).
@router.put("/subjects/{code}", response_model=SubjectCreateResponse)
async def upsert_subject(
    code: str,
    body: SubjectUpsertRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> SubjectCreateResponse:
    row = await one(
        session,
        """
        OPTIONAL MATCH (old:Subject {code: $code})
        WITH old IS NULL AS created
        MERGE (su:Subject {code: $code})
        SET su.name = $name, su.ects = $ects
        RETURN su.code AS code, su.name AS name, su.ects AS ects, created
        """,
        code=code,
        name=body.name,
        ects=body.ects,
    )
    if row.pop("created"):
        response.status_code = 201
        _location(request, response, "subject_detail", code=row["code"])
    return SubjectCreateResponse(**row)


@router.post("/curriculum-terms", response_model=CurriculumTermCreateResponse, status_code=201)
async def create_term(
    body: CurriculumTermCreateRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> CurriculumTermCreateResponse:
    if body.cycle_id is None:
        raise invalid("cycle_id is required")
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
        id=await next_id(session, "CurriculumTerm"),
        sem=body.sem,
    )
    if row is None:
        raise not_found("Curriculum or cycle")
    return CurriculumTermCreateResponse(**row)


@router.post("/curricula", response_model=CurriculumCreateResponse, status_code=201)
async def create_curriculum(
    body: CurriculumCreateRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> CurriculumCreateResponse:
    row = await one(
        session,
        """
        MATCH (p:Programme {id: $programme_id})
        CREATE (c:Curriculum {id: $id, intake_year: $intake_year})
        CREATE (p)-[:HAS_CURRICULUM]->(c)
        RETURN c.id AS id, p.id AS programme_id, c.intake_year AS intake_year
        """,
        programme_id=body.programme_id,
        id=await next_id(session, "Curriculum"),
        intake_year=body.intake_year,
    )
    if row is None:
        raise not_found("Programme")
    return CurriculumCreateResponse(**row)


@router.post("/faculties", response_model=FacultyCreateResponse, status_code=201)
async def create_faculty(
    body: FacultyCreateRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> FacultyCreateResponse:
    row = await one(
        session,
        """
        CREATE (fa:Faculty {id: $id, name: $name, full_name: $full_name})
        RETURN fa.id AS id, fa.name AS name, fa.full_name AS full_name
        """,
        id=await next_id(session, "Faculty"),
        name=body.name,
        full_name=body.full_name,
    )
    return FacultyCreateResponse(**row)


@router.post("/registrations", response_model=StartRegistrationsResponse, status_code=201)
async def start_registrations(
    body: StartRegistrationsRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> StartRegistrationsResponse:
    registration_id = await next_id(session, "Registration")
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
    # All three writes in one transaction: an error in any of them rolls back the others.
    tx = await session.begin_transaction()
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
            raise not_found("Cycle or faculty")
        await tx_one(
            tx,
            """
            MATCH (reg:Registration {id: $registration_id})
            UNWIND $turns AS turn
            CREATE (rt:RegistrationTurn {
              id: turn.id, turn_number: turn.turn_number, date: date(turn.date),
              start_time: time(turn.start), end_time: time(turn.end)
            })
            CREATE (reg)-[:HAS_TURN]->(rt)
            RETURN count(rt) AS created
            """,
            registration_id=registration_id,
            turns=turns,
        )
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
            raise not_found(f"Groups {', '.join(missing)}")
        await tx.commit()
    finally:
        # Closing a transaction that was not committed rolls it back.
        await tx.close()
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
          g.start_time AS start,
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


@router.post("/admins", response_model=AdminCreateResponse, status_code=201)
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
    except ConstraintError as exc:
        raise _idx_conflict(exc, body.idx) from exc
    return AdminCreateResponse(**row)


@router.delete("/users/{idx}", status_code=204)
async def remove_user_account(
    idx: str,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> None:
    """Delete the login account; the person node and its history stay in the graph."""
    if idx == caller.idx:
        raise conflict("Cannot remove your own account")
    row = await one(
        session,
        """
        MATCH (u:User {idx: $idx})
        REMOVE u:User:Inactive, u.email, u.passwd_hash, u.deactivated_at
        RETURN u.idx AS idx
        """,
        idx=idx,
    )
    if row is None:
        raise not_found("Account")


@router.post("/programmes", response_model=ProgrammeCreateResponse, status_code=201)
async def create_programme(
    body: ProgrammeCreateRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> ProgrammeCreateResponse:
    row = await one(
        session,
        """
        MATCH (fa:Faculty {id: $faculty_id})
        CREATE (p:Programme {id: $id, name: $name})-[:OFFERED_BY]->(fa)
        RETURN p.id AS id, p.name AS name, fa.id AS faculty_id
        """,
        faculty_id=body.faculty_id,
        id=await next_id(session, "Programme"),
        name=body.name,
    )
    if row is None:
        raise not_found("Faculty")
    return ProgrammeCreateResponse(**row)


@router.post("/curriculum-terms/subjects", response_model=TermSubjectResponse, status_code=201)
async def add_subject_to_term(
    body: TermSubjectRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> TermSubjectResponse:
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
    if row is None:
        raise not_found("Term or subject")
    if row["already"]:
        raise conflict("Subject already in this term")
    return TermSubjectResponse(**body.model_dump())


@router.post("/students/{idx}/enrolments", response_model=EnrolStudentResponse, status_code=201)
async def enrol_student(
    idx: str,
    body: EnrolStudentRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> EnrolStudentResponse:
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
        student_idx=idx,
        term_id=body.term_id,
    )
    if row is None:
        raise not_found("Student or term")
    if row["already"]:
        raise conflict("Student already enrolled in this term")
    return EnrolStudentResponse(student_idx=idx, term_id=body.term_id)


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


# Idempotent (MERGE): students already in this turn stay in it and are reported as assigned.
@router.post("/registrations/turns/students", response_model=AssignTurnResponse)
async def assign_students_to_turn(
    body: AssignTurnRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> AssignTurnResponse:
    if not body.student_idxs:
        raise invalid("No students given")
    row = await one(session, _ASSIGN_TURN, turn_id=body.turn_id, student_idxs=body.student_idxs)
    if row is None:
        raise not_found("Registration turn")
    if row["missing"]:
        raise not_found(f"Students {', '.join(row['missing'])}")
    if row["conflicts"]:
        raise conflict(
            f"Already assigned to another turn of this registration: {', '.join(row['conflicts'])}"
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
               rt.date AS date, rt.start_time AS start, rt.end_time AS end
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


@router.post("/groups/students", response_model=DeanRegisterResponse, status_code=201)
async def dean_register(
    body: DeanRegisterRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> DeanRegisterResponse:
    row = await one(
        session,
        _DEAN_REGISTER,
        student_idx=body.student_idx,
        group_id=body.group_id,
        ignore_capacity=body.ignore_capacity,
    )
    if row is None:
        raise not_found("Student or group")
    errors = {
        "already": "Student is already registered in this group",
        "conflict": "Student is already registered in another group of this type for this subject",
        "full": "Group is full",
    }
    if row["status"] in errors:
        raise conflict(errors[row["status"]])
    return DeanRegisterResponse(**body.model_dump())


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
