# Admin endpoints

See `user_endpoints.md` for conventions. Every endpoint here is allowed for Admin only. Admins can also use the teacher endpoints and `POST /opinions` (see the other files).

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
	"g_type": String,
	"weight": Float
}
```

**Response**

```json
{
	"id": String,
	"subject_code": String,
	"g_type": String,
	"weight": Float,
	"err": String?
}
```

Fails if the subject already has a group type with that name.

**Query**

```cypher
// 1. Duplicate check
MATCH (su:Subject {code: $subject_code})-[:HAS_TYPE]->(gt:GroupType {g_type: $g_type})
RETURN gt.id AS id

// 2. Create
MATCH (su:Subject {code: $subject_code})
CREATE (gt:GroupType {id: $id, g_type: $g_type, weight: $weight})
CREATE (su)-[:HAS_TYPE]->(gt)
RETURN gt.id AS id, su.code AS subject_code, gt.g_type AS g_type, gt.weight AS weight
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

Fails if the subject has no group type named `g_type`, or if no curriculum term taught in the cycle includes the subject.

**Query**

```cypher
MATCH (su:Subject {code: $subject_code})-[:HAS_TYPE]->(gt:GroupType {g_type: $g_type})
MATCH (ac:AcademicCycle {id: $cycle_id})
WHERE EXISTS { (su)<-[:INCLUDES]-(:CurriculumTerm)-[:TAUGHT_IN]->(ac) }
MATCH (r:Room {id: $room_id})
CREATE (g:Group {
  id: $id, weekday: $weekday, number: $number, pnp: $pnp,
  capacity: $capacity, start_hr: time($start_hr), end_time: time($end_time)
})-[:OF_TYPE]->(gt),
(g)-[:IN_ROOM]->(r),
(g)-[:IN_CYCLE]->(ac)
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
	"season": String
}
```

**Response**

```json
{
	"id": String,
	"year": String,
	"season": String,
	"err": String?
}
```

**Query**

```cypher
CREATE (ac:AcademicCycle {id: $id, year: $year, season: $season})
RETURN ac.id AS id, ac.year AS year, ac.season AS season
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
		"season": String
	}
}
```

**Query**

```cypher
MATCH (ac:AcademicCycle)
RETURN ac.id AS id, ac.year AS year, ac.season AS season
ORDER BY ac.year, ac.season
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

`label` is built by the server as `"<subject code> <type> #<number> (day <weekday>)"`.

**Query**

```cypher
MATCH (g:Group)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(su:Subject)
RETURN
  g.id AS id,
  su.code AS course_code,
  gt.g_type AS g_type,
  g.number AS number,
  g.weekday AS weekday
ORDER BY su.code, gt.g_type, g.number
```
