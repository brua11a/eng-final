# Admin endpoints

See `user_endpoints.md` for conventions. Every endpoint here is allowed for Admin only. Admins can also use the teacher endpoints and `POST /opinions` (requires `student_idx`, `group_id`, and `teacher_idx`; see `student_endpoints.md`).

Time and DateTime inputs without a UTC offset are stored as `+01:00`.

---

## POST /admin/teachers

**Allowed:** Admin

**Request**

```json
{
	"name": String,
	"surname": String,
	"phone": String,
	"degree": String,
	"photo": String?,
	"working_since": Date,
	"faculty_id": String
}
```

**Response**

```json
{
	"idx": String,
	"name": String,
	"surname": String,
	"phone": String,
	"degree": String,
	"photo": String?,
	"working_since": Date,
	"faculty_id": String,
	"err": String?
}
```

**Query**

```cypher
// 1. Next teacher idx ("T" + number)
OPTIONAL MATCH (t:Teacher)
RETURN coalesce(max(toInteger(substring(t.idx, 1))), 0) + 1 AS n

// 2. Create
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
```

---

## POST /admin/students

**Allowed:** Admin

**Request**

```json
{
	"name": String,
	"surname": String,
	"phone": String,
	"photo": String?,
	"joined": DateTime,
	"programme": String,
	"term_id": String?
}
```

`programme` is a programme id. Without `term_id`, the student is enrolled in semester 1 of that programme's newest curriculum. With `term_id`, they are enrolled in that term, which must belong to one of the programme's curricula (for students joining partway through).

**Response**

```json
{
	"idx": String,
	"name": String,
	"surname": String,
	"phone": String,
	"photo": String?,
	"joined": DateTime,
	"err": String?
}
```

**Query**

```cypher
// 1. Next student idx (number)
OPTIONAL MATCH (st:Student)
RETURN coalesce(max(toInteger(st.idx)), 0) + 1 AS n

// 2. Resolve the term. The server takes the first entry of `terms`, and reports
//    "Programme not found", "Programme has no curriculum", "Programme has no first semester"
//    or "Term does not belong to this programme" when it cannot.
MATCH (p:Programme {id: $programme})
RETURN
  COUNT { (p)-[:HAS_CURRICULUM]->(:Curriculum) } AS curricula,
  COLLECT {
    MATCH (p)-[:HAS_CURRICULUM]->(c:Curriculum)-[:HAS_TERM]->(ct:CurriculumTerm)
    WHERE ($term_id IS NULL AND ct.sem = 1) OR ct.id = $term_id
    RETURN ct.id ORDER BY c.intake_year DESC
  } AS terms

// 3. Create and enrol
MATCH (ct:CurriculumTerm {id: $term_id})
CREATE (st:Student:Person {
  idx: $idx, name: $name, surname: $surname, phone: $phone,
  joined: datetime($joined), photo: $photo
})
CREATE (st)-[:ENROLLED]->(ct)
RETURN st.idx AS idx, st.name AS name, st.surname AS surname,
       st.phone AS phone, st.photo AS photo, st.joined AS joined
```

---

## POST /admin/users

**Allowed:** Admin

Gives an existing person a login.

**Request**

```json
{
	"email": String,
	"passwd": String,
	"idx": String
}
```

**Response**

```json
{
	"email": String,
	"idx": String,
	"roles": List["Admin" | "Teacher" | "Student"],
	"err": String?
}
```

**Query**

```cypher
MATCH (owner:Person {idx: $idx})
SET owner:User, owner.email = $email, owner.passwd_hash = $passwd_hash
RETURN owner.email AS email,
  owner.idx AS idx,
  owner:Admin AS admin,
  owner:Teacher AS teacher,
  owner:Student AS student
```

---

## POST /admin/users/deactivate

**Allowed:** Admin

**Request**

```json
{
	"idx": String
}
```

**Response**

```json
{
	"idx": String,
	"err": String?
}
```

**Query**

```cypher
MATCH (u:User {idx: $idx})
SET u:Inactive, u.deactivated_at = datetime()
RETURN u.idx AS idx
```

---

## POST /admin/users/activate

**Allowed:** Admin

**Request**

```json
{
	"idx": String
}
```

**Response**

```json
{
	"idx": String,
	"err": String?
}
```

**Query**

```cypher
MATCH (u:User {idx: $idx})
REMOVE u:Inactive, u.deactivated_at
RETURN u.idx AS idx
```

---

## POST /admin/users/roles

**Allowed:** Admin

**Request**

```json
{
	"idx": String,
	"role": "Admin" | "Teacher" | "Student",
	"degree": String?,
	"working_since": Date?,
	"joined": DateTime?
}
```

`degree` and `working_since` are required when adding Teacher. `joined` is required when adding Student.

**Response**

```json
{
	"idx": String,
	"email": String?,
	"roles": List["Admin" | "Teacher" | "Student"],
	"err": String?
}
```

**Query**

```cypher
// 1. Current roles
MATCH (p:Person {idx: $idx})
RETURN p:Admin AS admin, p:Teacher AS teacher, p:Student AS student, p.email AS email

// 2a. Add Admin
MATCH (p:Person {idx: $idx})
SET p:Admin
RETURN p.idx AS idx, p.email AS email, p:Admin AS admin, p:Teacher AS teacher, p:Student AS student

// 2b. Add Teacher
MATCH (p:Person {idx: $idx})
SET p:Teacher, p.degree = $degree, p.working_since = date($working_since)
RETURN p.idx AS idx, p.email AS email, p:Admin AS admin, p:Teacher AS teacher, p:Student AS student

// 2c. Add Student
MATCH (p:Person {idx: $idx})
SET p:Student, p.joined = datetime($joined)
RETURN p.idx AS idx, p.email AS email, p:Admin AS admin, p:Teacher AS teacher, p:Student AS student
```

---

## POST /admin/users/roles/remove

**Allowed:** Admin

**Request**

```json
{
	"idx": String,
	"role": "Admin" | "Teacher" | "Student"
}
```

**Response**

```json
{
	"idx": String,
	"email": String?,
	"roles": List["Admin" | "Teacher" | "Student"],
	"err": String?
}
```

Fails if the person does not have the role, or if it is their last role.

**Query**

```cypher
// 1. Current roles
MATCH (p:Person {idx: $idx})
RETURN p:Admin AS admin, p:Teacher AS teacher, p:Student AS student, p.email AS email

// 2. Remove one label (Admin, Teacher or Student)
MATCH (p:Person {idx: $idx})
REMOVE p:Admin
RETURN p.idx AS idx, p.email AS email, p:Admin AS admin, p:Teacher AS teacher, p:Student AS student
```

---

## POST /admin/group-types

**Allowed:** Admin

**Request**

```json
{
	"subject_code": String,
	"cycle_id": String,
	"g_type": String,
	"weight": Float
}
```

**Response**

```json
{
	"id": String,
	"subject_code": String,
	"cycle_id": String,
	"g_type": String,
	"weight": Float,
	"err": String?
}
```

Group types belong to a subject in one cycle, so weights can change from cycle to cycle. The subject's instance for the cycle is created with its first group type. Fails if the subject already has a group type with that name in that cycle, or if no curriculum term taught in the cycle includes the subject.

**Query**

```cypher
// 1. Duplicate check
MATCH (:Subject {code: $subject_code})<-[:INSTANCE_OF]-(si:SubjectInstance)-[:OFFERED_IN]->(:AcademicCycle {id: $cycle_id})
MATCH (si)-[:HAS_TYPE]->(gt:GroupType {g_type: $g_type})
RETURN gt.id AS id

// 2. Create, reusing the subject's instance for the cycle if it exists
MATCH (su:Subject {code: $subject_code})
MATCH (ac:AcademicCycle {id: $cycle_id})
WHERE EXISTS { (su)<-[:INCLUDES]-(:CurriculumTerm)-[:TAUGHT_IN]->(ac) }
MERGE (su)<-[:INSTANCE_OF]-(si:SubjectInstance)-[:OFFERED_IN]->(ac)
  ON CREATE SET si.id = $instance_id
CREATE (si)-[:HAS_TYPE]->(gt:GroupType {id: $id, g_type: $g_type, weight: $weight})
RETURN gt.id AS id, su.code AS subject_code, ac.id AS cycle_id,
       gt.g_type AS g_type, gt.weight AS weight
```

---

## POST /admin/groups

**Allowed:** Admin

**Request**

```json
{
	"weekday": Integer,
	"g_type": String,
	"number": Integer,
	"pnp": String,
	"capacity": Integer,
	"start_hr": Time,
	"end_time": Time,
	"subject_code": String,
	"cycle_id": String,
	"room_id": String
}
```

**Response**

```json
{
	"id": String,
	"weekday": Integer,
	"g_type": String,
	"number": Integer,
	"pnp": String,
	"capacity": Integer,
	"start_hr": Time,
	"end_time": Time,
	"subject_code": String,
	"cycle_id": String,
	"room_id": String,
	"err": String?
}
```

Fails if the room doesn't exist, or if the subject has no group type named `g_type` in that cycle (create it with `POST /admin/group-types` first).

**Query**

```cypher
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
```

---

## POST /admin/groups/teachers

**Allowed:** Admin

**Request**

```json
{
	"teacher_idx": String,
	"group_id": String
}
```

**Response**

```json
{
	"teacher_idx": String,
	"group_id": String,
	"err": String?
}
```

**Query**

```cypher
MATCH (t:Teacher {idx: $teacher_idx})
MATCH (g:Group {id: $group_id})
MERGE (t)-[:TEACHES]->(g)
RETURN t.idx AS teacher_idx, g.id AS group_id
```

---

## POST /admin/rooms

**Allowed:** Admin

**Request**

```json
{
	"building": String,
	"room_num": String
}
```

**Response**

```json
{
	"id": String,
	"building": String,
	"room_num": String,
	"err": String?
}
```

**Query**

```cypher
CREATE (r:Room {id: $id, building: $building, room_num: $room_num})
RETURN r.id AS id, r.building AS building, r.room_num AS room_num
```

---

## POST /admin/academic-cycles

**Allowed:** Admin

**Request**

```json
{
	"year": String,
	"season": String,
	"start_date": Date,
	"end_date": Date
}
```

`start_date` and `end_date` bound the teaching period; the weekly schedule shows a cycle's classes only between them. Fails if `end_date` is not after `start_date`.

**Response**

```json
{
	"id": String,
	"year": String,
	"season": String,
	"start_date": Date,
	"end_date": Date,
	"err": String?
}
```

**Query**

```cypher
CREATE (ac:AcademicCycle {
  id: $id, year: $year, season: $season,
  start_date: date($start_date), end_date: date($end_date)
})
RETURN ac.id AS id, ac.year AS year, ac.season AS season,
       ac.start_date AS start_date, ac.end_date AS end_date
```

---

## POST /admin/subjects

**Allowed:** Admin

Creates the subject, or updates its name and ECTS if the code already exists.

**Request**

```json
{
	"code": String,
	"name": String,
	"ects": Integer?
}
```

**Response**

```json
{
	"code": String,
	"name": String,
	"ects": Integer?,
	"err": String?
}
```

**Query**

```cypher
MERGE (su:Subject {code: $code})
SET su.name = $name, su.ects = $ects
RETURN su.code AS code, su.name AS name, su.ects AS ects
```

---

## POST /admin/curriculum-terms

**Allowed:** Admin

**Request**

```json
{
	"sem": Integer,
	"curriculum_id": String,
	"cycle_id": String
}
```

**Response**

```json
{
	"id": String,
	"sem": Integer,
	"curriculum_id": String,
	"cycle_id": String?,
	"err": String?
}
```

**Query**

```cypher
MATCH (c:Curriculum {id: $curriculum_id})
MATCH (ac:AcademicCycle {id: $cycle_id})
CREATE (ct:CurriculumTerm {id: $id, sem: $sem})
CREATE (c)-[:HAS_TERM]->(ct)
CREATE (ct)-[:TAUGHT_IN]->(ac)
RETURN ct.id AS id, ct.sem AS sem, c.id AS curriculum_id, ac.id AS cycle_id
```

---

## POST /admin/curricula

**Allowed:** Admin

**Request**

```json
{
	"programme_id": String,
	"intake_year": String
}
```

**Response**

```json
{
	"id": String,
	"programme_id": String,
	"intake_year": String,
	"err": String?
}
```

**Query**

```cypher
MATCH (p:Programme {id: $programme_id})
CREATE (c:Curriculum {id: $id, intake_year: $intake_year})
CREATE (p)-[:HAS_CURRICULUM]->(c)
RETURN c.id AS id, p.id AS programme_id, c.intake_year AS intake_year
```

---

## POST /admin/faculties

**Allowed:** Admin

**Request**

```json
{
	"name": String,
	"full_name": String
}
```

**Response**

```json
{
	"id": String,
	"name": String,
	"full_name": String,
	"err": String?
}
```

**Query**

```cypher
CREATE (fa:Faculty {id: $id, name: $name, full_name: $full_name})
RETURN fa.id AS id, fa.name AS name, fa.full_name AS full_name
```

---

## POST /admin/registrations

**Allowed:** Admin

Creates a registration with its turns and opened groups in one transaction. Nothing is saved if any step fails.

**Request**

```json
{
	"name": String,
	"cycle_id": String,
	"faculty_id": String,
	"reg_type": "zapisowa",
	"turns": List[RegistrationTurn],
	"group_ids": List[String]

	RegistrationTurn = {
		"turn_number": Integer,
		"date": Date,
		"start": Time,
		"end": Time
	}
}
```

**Response**

```json
{
	"id": String?,
	"name": String?,
	"reg_type": "zapisowa"?,
	"turns": List[RegistrationTurn],
	"group_ids": List[String],
	"err": String?
}
```

**Query**

```cypher
// 1. Registration
MATCH (ac:AcademicCycle {id: $cycle_id})
MATCH (fa:Faculty {id: $faculty_id})
CREATE (reg:Registration {id: $id, name: $name, reg_type: $reg_type})
CREATE (reg)-[:FOR_CYCLE]->(ac)
CREATE (reg)-[:FOR_FACULTY]->(fa)
RETURN reg.id AS id

// 2. All turns at once ($turns: list of {id, turn_number, date, start, end})
MATCH (reg:Registration {id: $registration_id})
UNWIND $turns AS turn
CREATE (rt:RegistrationTurn {
  id: turn.id, turn_number: turn.turn_number, date: date(turn.date),
  start_hr: time(turn.start), end_time: time(turn.end)
})
CREATE (reg)-[:HAS_TURN]->(rt)
RETURN count(rt) AS created

// 3. All groups at once. Any id missing from `found` rolls the transaction back
//    with "Groups not found: <ids>".
MATCH (reg:Registration {id: $registration_id})
UNWIND $group_ids AS group_id
MATCH (g:Group {id: group_id})
MERGE (reg)-[:OPENS]->(g)
RETURN collect(g.id) AS found
```

---

## GET /admin/programmes

**Allowed:** Admin

**Request**

None.

**Response**

```json
{
	"programmes": List[Programme]

	Programme = {
		"id": String,
		"name": String,
		"faculty_id": String
	}
}
```

**Query**

```cypher
MATCH (p:Programme)-[:OFFERED_BY]->(fa:Faculty)
RETURN p.id AS id, p.name AS name, fa.id AS faculty_id
ORDER BY p.name
```

---

## GET /admin/rooms

**Allowed:** Admin

**Request**

None.

**Response**

```json
{
	"rooms": List[Room]

	Room = {
		"id": String,
		"building": String,
		"room_num": String
	}
}
```

**Query**

```cypher
MATCH (r:Room)
RETURN r.id AS id, r.building AS building, r.room_num AS room_num
ORDER BY r.building, r.room_num
```

---

## GET /admin/academic-cycles

**Allowed:** Admin

**Request**

None.

**Response**

```json
{
	"cycles": List[AcademicCycle]

	AcademicCycle = {
		"id": String,
		"year": String,
		"season": String,
		"start_date": Date?,
		"end_date": Date?
	}
}
```

**Query**

```cypher
MATCH (ac:AcademicCycle)
RETURN ac.id AS id, ac.year AS year, ac.season AS season,
       ac.start_date AS start_date, ac.end_date AS end_date
ORDER BY ac.start_date
```

---

## GET /admin/subjects

**Allowed:** Admin

**Request**

None.

**Response**

```json
{
	"subjects": List[Subject]

	Subject = {
		"code": String,
		"name": String
	}
}
```

**Query**

```cypher
MATCH (su:Subject)
RETURN su.code AS code, su.name AS name
ORDER BY su.code
```

---

## GET /admin/curricula

**Allowed:** Admin

**Request**

None.

**Response**

```json
{
	"curricula": List[Curriculum]

	Curriculum = {
		"id": String,
		"programme_name": String,
		"intake_year": String
	}
}
```

**Query**

```cypher
MATCH (c:Curriculum)<-[:HAS_CURRICULUM]-(p:Programme)
RETURN c.id AS id, p.name AS programme_name, c.intake_year AS intake_year
ORDER BY p.name, c.intake_year DESC
```

---

## GET /admin/teachers

**Allowed:** Admin

**Request**

None.

**Response**

```json
{
	"teachers": List[Teacher]

	Teacher = {
		"idx": String,
		"name": String,
		"surname": String
	}
}
```

**Query**

```cypher
MATCH (t:Teacher)
RETURN t.idx AS idx, t.name AS name, t.surname AS surname
ORDER BY t.surname, t.name
```

---

## GET /admin/groups

**Allowed:** Admin

**Request**

None.

**Response**

```json
{
	"groups": List[Group]

	Group = {
		"id": String,
		"label": String
	}
}
```

`label` is built by the server as `"<subject code> <subject name>, <cycle>, <type> #<number>, <Mon..Sun> <start>-<end>"`.

**Query**

```cypher
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
```

---

## POST /admin/admins

**Allowed:** Admin

Creates an administrator person. A login is assigned separately with `POST /admin/users`.

**Request**

```json
{
	"name": String,
	"surname": String,
	"phone": String
}
```

**Response**

```json
{
	"idx": String?,
	"name": String,
	"surname": String,
	"phone": String,
	"err": String?
}
```

**Query**

```cypher
// 1. Next admin idx ("A" + 3 digits)
OPTIONAL MATCH (p:Person) WHERE p.idx STARTS WITH "A"
RETURN coalesce(max(toInteger(substring(p.idx, 1))), 0) + 1 AS n

// 2. Create
CREATE (a:Admin:Person {idx: $idx, name: $name, surname: $surname, phone: $phone})
RETURN a.idx AS idx, a.name AS name, a.surname AS surname, a.phone AS phone
```

---

## POST /admin/users/remove

**Allowed:** Admin (not on their own account)

Deletes the login account. The person node, its roles and its history (registrations, grades, opinions) stay in the graph.

**Request**

```json
{
	"idx": String
}
```

**Response**

```json
{
	"idx": String,
	"err": String?
}
```

**Query**

```cypher
MATCH (u:User {idx: $idx})
REMOVE u:User:Inactive, u.email, u.passwd_hash, u.deactivated_at
RETURN u.idx AS idx
```

---

## POST /admin/programmes

**Allowed:** Admin

**Request**

```json
{
	"name": String,
	"faculty_id": String
}
```

**Response**

```json
{
	"id": String?,
	"name": String,
	"faculty_id": String,
	"err": String?
}
```

**Query**

```cypher
MATCH (fa:Faculty {id: $faculty_id})
CREATE (p:Programme {id: $id, name: $name})-[:OFFERED_BY]->(fa)
RETURN p.id AS id, p.name AS name, fa.id AS faculty_id
```

---

## POST /admin/curriculum-terms/subjects

**Allowed:** Admin

Adds a subject to a curriculum term. Required before a group type can be created for that subject in the term's cycle.

**Request**

```json
{
	"term_id": String,
	"subject_code": String
}
```

**Response**

```json
{
	"term_id": String,
	"subject_code": String,
	"err": String?
}
```

**Query**

```cypher
MATCH (ct:CurriculumTerm {id: $term_id})
MATCH (su:Subject {code: $subject_code})
WITH ct, su, EXISTS { (ct)-[:INCLUDES]->(su) } AS already
MERGE (ct)-[:INCLUDES]->(su)
RETURN already
```

---

## POST /admin/students/enrol

**Allowed:** Admin

Enrols an existing student in a curriculum term (e.g. the next semester).

**Request**

```json
{
	"student_idx": String,
	"term_id": String
}
```

**Response**

```json
{
	"student_idx": String,
	"term_id": String,
	"err": String?
}
```

**Query**

```cypher
MATCH (st:Student {idx: $student_idx})
MATCH (ct:CurriculumTerm {id: $term_id})
WITH st, ct, EXISTS { (st)-[:ENROLLED]->(ct) } AS already
MERGE (st)-[:ENROLLED]->(ct)
RETURN already
```

---

## POST /admin/registrations/turns/students

**Allowed:** Admin

Assigns students to a registration turn. All-or-nothing: fails if any student does not exist or is already assigned to another turn of the same registration.

**Request**

```json
{
	"turn_id": String,
	"student_idxs": List[String]
}
```

**Response**

```json
{
	"turn_id": String,
	"assigned": List[String],
	"err": String?
}
```

**Query**

```cypher
// 1. Validation
MATCH (rt:RegistrationTurn {id: $turn_id})<-[:HAS_TURN]-(reg:Registration)
UNWIND $student_idxs AS sidx
OPTIONAL MATCH (st:Student {idx: sidx})
WITH sidx, st, EXISTS {
  MATCH (st)-[:ASSIGNED]->(other:RegistrationTurn)<-[:HAS_TURN]-(reg)
  WHERE other <> rt
} AS other_turn
RETURN
  [x IN collect({idx: sidx, found: st IS NOT NULL}) WHERE NOT x.found | x.idx] AS missing,
  [x IN collect({idx: sidx, other: other_turn}) WHERE x.other | x.idx] AS conflicts

// 2. Assign
MATCH (rt:RegistrationTurn {id: $turn_id})
UNWIND $student_idxs AS sidx
MATCH (st:Student {idx: sidx})
MERGE (st)-[:ASSIGNED]->(rt)
RETURN collect(DISTINCT st.idx) AS assigned
```

---

## GET /admin/students

**Allowed:** Admin

**Response**

```json
{
	"students": List[{ "idx": String, "name": String, "surname": String }]
}
```

**Query**

```cypher
MATCH (st:Student)
RETURN st.idx AS idx, st.name AS name, st.surname AS surname
ORDER BY st.surname, st.name
```

---

## GET /admin/curriculum-terms

**Allowed:** Admin

**Response**

```json
{
	"terms": List[{ "id": String, "label": String }]
}
```

`label` is built by the server as `"<programme> <intake year>, sem. <n> (<cycle>)"`.

**Query**

```cypher
MATCH (p:Programme)-[:HAS_CURRICULUM]->(c:Curriculum)-[:HAS_TERM]->(ct:CurriculumTerm)
OPTIONAL MATCH (ct)-[:TAUGHT_IN]->(ac:AcademicCycle)
RETURN ct.id AS id, p.name AS programme, c.intake_year AS intake_year, ct.sem AS sem,
       ac.year AS year, ac.season AS season
ORDER BY p.name, c.intake_year DESC, ct.sem
```

---

## GET /admin/registration-turns

**Allowed:** Admin

**Response**

```json
{
	"turns": List[{ "id": String, "label": String }]
}
```

`label` is built by the server as `"<registration>, turn <n> (<date> <start>-<end>)"`.

**Query**

```cypher
MATCH (reg:Registration)-[:HAS_TURN]->(rt:RegistrationTurn)
RETURN rt.id AS id, reg.name AS registration, rt.turn_number AS turn_number,
       rt.date AS date, rt.start_hr AS start, rt.end_time AS end
ORDER BY rt.date DESC, reg.name, rt.turn_number
```

---

## POST /admin/groups/students

**Allowed:** Admin

Dean's office registration of a student to a group. Bypasses registration turns. A student can still be in only one group of each type per subject. Group capacity is enforced unless `ignore_capacity` is `true`.

**Request**

```json
{
	"student_idx": String,
	"group_id": String,
	"ignore_capacity": Boolean?
}
```

**Response**

```json
{
	"student_idx": String,
	"group_id": String,
	"ignore_capacity": Boolean,
	"err": String?
}
```

**Query**

```cypher
MATCH (st:Student {idx: $student_idx})
MATCH (g:Group {id: $group_id})-[:OF_TYPE]->(gt:GroupType)
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
```

