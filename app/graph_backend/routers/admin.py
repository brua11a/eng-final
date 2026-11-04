from datetime import datetime, time

from fastapi import APIRouter, Depends
from neo4j import AsyncSession
from neo4j.exceptions import Neo4jError

from app.database import get_session
from app.graph_backend.auth import hash_password, require, roles_from_flags
from app.graph_backend.query import next_id, one, run, tx_one
from app.schemas.academic_cycle import (
    AcademicCycleCreateRequest,
    AcademicCycleCreateResponse,
    AcademicCycleListResponse,
    MyAcademicCycleItem,
)
from app.schemas.auth import (
    AddRoleRequest,
    AddRoleResponse,
    AssignUserRequest,
    AssignUserResponse,
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
from app.schemas.faculty import FacultyCreateRequest, FacultyCreateResponse, FacultyItem, FacultyListResponse
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


async def _teacher_idx(session: AsyncSession) -> str:
    row = await one(
        session,
        "OPTIONAL MATCH (t:Teacher) RETURN coalesce(max(toInteger(substring(t.idx, 1))), 0) + 1 AS n",
    )
    return f"T{row['n']}"


async def _student_idx(session: AsyncSession) -> str:
    row = await one(
        session,
        "OPTIONAL MATCH (st:Student) RETURN coalesce(max(toInteger(st.idx)), 0) + 1 AS n",
    )
    return str(row["n"])


@router.post("/teachers", response_model=TeacherCreateResponse)
async def create_teacher(
    body: TeacherCreateRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> TeacherCreateResponse:
    idx = await _teacher_idx(session)
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
            faculty_id=body.faculty_id, err=db_err(exc),
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
    idx = await _student_idx(session)
    try:
        row = await one(
            session,
            """
            MATCH (p:Programme {id: $programme})-[:HAS_CURRICULUM]->(c:Curriculum)-[:HAS_TERM]->(ct:CurriculumTerm {sem: 1})
            WITH ct, c ORDER BY c.intake_year DESC LIMIT 1
            CREATE (st:Student:Person {
              idx: $idx, name: $name, surname: $surname, phone: $phone,
              joined: datetime($joined), photo: $photo
            })
            CREATE (st)-[:ENROLLED]->(ct)
            RETURN st.idx AS idx, st.name AS name, st.surname AS surname,
                   st.phone AS phone, st.photo AS photo, st.joined AS joined
            """,
            programme=body.programme,
            idx=idx,
            name=body.name,
            surname=body.surname,
            phone=body.phone,
            joined=_zoned_datetime(body.joined),
            photo=body.photo,
        )
    except Neo4jError as exc:
        return StudentCreateResponse(
            idx=idx, name=body.name, surname=body.surname, phone=body.phone,
            photo=body.photo, joined=body.joined, err=db_err(exc),
        )
    if row is None:
        return StudentCreateResponse(
            idx=idx, name=body.name, surname=body.surname, phone=body.phone,
            photo=body.photo, joined=body.joined, err="Programme has no first semester",
        )
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


@router.post("/group-types", response_model=GroupTypeCreateResponse)
async def create_group_type(
    body: GroupTypeCreateRequest,
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> GroupTypeCreateResponse:
    type_id = await next_id(session, "GroupType")
    try:
        existing = await one(
            session,
            """
            MATCH (su:Subject {code: $subject_code})-[:HAS_TYPE]->(gt:GroupType {g_type: $g_type})
            RETURN gt.id AS id
            """,
            subject_code=body.subject_code,
            g_type=body.g_type,
        )
        if existing is not None:
            return GroupTypeCreateResponse(
                id=existing["id"], subject_code=body.subject_code, g_type=body.g_type,
                weight=body.weight, err="Group type already exists",
            )
        row = await one(
            session,
            """
            MATCH (su:Subject {code: $subject_code})
            CREATE (gt:GroupType {id: $id, g_type: $g_type, weight: $weight})
            CREATE (su)-[:HAS_TYPE]->(gt)
            RETURN gt.id AS id, su.code AS subject_code, gt.g_type AS g_type, gt.weight AS weight
            """,
            subject_code=body.subject_code,
            id=type_id,
            g_type=body.g_type,
            weight=body.weight,
        )
    except Neo4jError as exc:
        return GroupTypeCreateResponse(
            id=type_id, subject_code=body.subject_code, g_type=body.g_type,
            weight=body.weight, err=db_err(exc),
        )
    if row is None:
        return GroupTypeCreateResponse(
            id=type_id, subject_code=body.subject_code, g_type=body.g_type,
            weight=body.weight, err="Subject not found",
        )
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
            MATCH (su:Subject {code: $subject_code})-[:HAS_TYPE]->(gt:GroupType {g_type: $g_type})
            MATCH (r:Room {id: $room_id})
            CREATE (g:Group {
              id: $id, weekday: $weekday, number: $number, pnp: $pnp,
              capacity: $capacity, start_hr: time($start_hr), end_time: time($end_time)
            })-[:OF_TYPE]->(gt),
            (g)-[:IN_ROOM]->(r)
            RETURN g.id AS id, g.weekday AS weekday, gt.g_type AS g_type, g.number AS number,
                   g.pnp AS pnp, g.capacity AS capacity, g.start_hr AS start_hr, g.end_time AS end_time,
                   su.code AS subject_code, r.id AS room_id
            """,
            subject_code=body.subject_code,
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
            subject_code=body.subject_code, room_id=body.room_id, err=db_err(exc),
        )
    if row is None:
        return GroupCreateResponse(
            id=group_id, weekday=body.weekday, g_type=body.g_type, number=body.number,
            pnp=body.pnp, capacity=body.capacity, start_hr=body.start_hr, end_time=body.end_time,
            subject_code=body.subject_code, room_id=body.room_id, err="Group type or room not found",
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
    try:
        row = await one(
            session,
            """
            CREATE (ac:AcademicCycle {id: $id, year: $year, season: $season})
            RETURN ac.id AS id, ac.year AS year, ac.season AS season
            """,
            id=cycle_id,
            year=body.year,
            season=body.season,
        )
    except Neo4jError as exc:
        return AcademicCycleCreateResponse(id=cycle_id, year=body.year, season=body.season, err=db_err(exc))
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
        for turn in body.turns:
            turn_id = await next_id(session, "RegistrationTurn")
            written = await tx_one(
                tx,
                """
                MATCH (reg:Registration {id: $registration_id})
                CREATE (rt:RegistrationTurn {
                  id: $turn_id, turn_number: $turn_number, date: date($date),
                  start_hr: time($start), end_time: time($end)
                })
                CREATE (reg)-[:HAS_TURN]->(rt)
                RETURN rt.id AS id
                """,
                registration_id=registration_id,
                turn_id=turn_id,
                turn_number=turn.turn_number,
                date=turn.date.isoformat(),
                start=_zoned_time(turn.start),
                end=_zoned_time(turn.end),
            )
            if written is None:
                await tx.rollback()
                return StartRegistrationsResponse(err="Could not create a registration turn")
        for group_id in body.group_ids:
            opened = await tx_one(
                tx,
                """
                MATCH (reg:Registration {id: $registration_id})
                MATCH (g:Group {id: $group_id})
                MERGE (reg)-[:OPENS]->(g)
                RETURN g.id AS id
                """,
                registration_id=registration_id,
                group_id=group_id,
            )
            if opened is None:
                await tx.rollback()
                return StartRegistrationsResponse(err=f"Group {group_id} not found")
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


@router.get("/faculties", response_model=FacultyListResponse)
async def list_faculties(
    session: AsyncSession = Depends(get_session),
    caller=Depends(_admin),
) -> FacultyListResponse:
    rows = await run(
        session,
        "MATCH (fa:Faculty) RETURN fa.id AS id, fa.name AS name, fa.full_name AS full_name ORDER BY fa.name",
    )
    return FacultyListResponse(faculties=[FacultyItem(**row) for row in rows])


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
        "MATCH (ac:AcademicCycle) RETURN ac.id AS id, ac.year AS year, ac.season AS season ORDER BY ac.year, ac.season",
    )
    return AcademicCycleListResponse(cycles=[MyAcademicCycleItem(**row) for row in rows])
