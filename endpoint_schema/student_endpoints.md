# Student endpoints

See `user_endpoints.md` for conventions. `$student_idx` is always the caller's own idx, taken from the token.

---

## GET /me/registrations

**Allowed:** Student

**Request**

None.

**Response**

```json
{
	"available_registrations": List[RegistrationItem]

	RegistrationItem = {
		"id": String,
		"name": String,
		"reg_type": "zapisowa",
		"curriculum_id": String?,
		"turn_number": Integer,
		"date": Date,
		"start": Time,
		"end": Time
	}
}
```

**Query**

```cypher
MATCH (st:Student {idx: $student_idx})-[:ASSIGNED]->(rt:RegistrationTurn)<-[:HAS_TURN]-(reg:Registration)
RETURN
  reg.id AS id,
  reg.name AS name,
  reg.reg_type AS reg_type,
  head(COLLECT {
    MATCH (reg)-[:FOR_FACULTY]->(:Faculty)<-[:OFFERED_BY]-(:Programme)-[:HAS_CURRICULUM]->(c:Curriculum)
          -[:HAS_TERM]->(:CurriculumTerm)<-[:ENROLLED]-(st)
    RETURN c.id
  }) AS curriculum_id,
  rt.turn_number AS turn_number,
  rt.date AS date,
  rt.start_hr AS start,
  rt.end_time AS end
```

---

## POST /me/registrations/courses

**Allowed:** Student, only for registrations they have a turn in (403 otherwise)

**Request**

```json
{
	"registration_id": String
}
```

**Response**

```json
{
	"courses": List[Course]

	Course = {
		"id": String,
		"name": String,
		"classes": List[ClassInfo],
		"academic_cycle": String
	}

	ClassInfo = {
		"g_type": String,
		"count": Integer
	}
}
```

`Course.id` is the subject code. `classes` counts the open groups of each type.

**Query**

```cypher
// 1. Access check
MATCH (st:Student {idx: $student_idx})-[:ASSIGNED]->(:RegistrationTurn)<-[:HAS_TURN]-(reg:Registration {id: $registration_id})
RETURN reg.id AS id

// 2. Groups opened by the registration, one row per group
MATCH (reg:Registration {id: $registration_id})-[:FOR_CYCLE]->(ac:AcademicCycle)
MATCH (reg)-[:OPENS]->(g:Group)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(si:SubjectInstance)-[:OFFERED_IN]->(ac)
MATCH (si)-[:INSTANCE_OF]->(su:Subject)
RETURN
  su.code AS subject_code,
  su.name AS subject_name,
  gt.g_type AS g_type,
  ac.year AS cycle_year,
  ac.season AS cycle_season
```

---

## POST /me/registrations/groups

**Allowed:** Student, only for registrations they have a turn in (403 otherwise)

**Request**

```json
{
	"registration_id": String,
	"subject_code": String
}
```

**Response**

```json
{
	"groups": List[OpenGroup]

	OpenGroup = {
		"id": String,
		"g_type": String,
		"number": Integer,
		"weekday": Integer,
		"start": Time,
		"end": Time,
		"capacity": Integer,
		"filled": Integer,
		"room": String?,
		"teacher": String?,
		"registered": Boolean
	}
}
```

**Query**

```cypher
// 1. Access check
MATCH (st:Student {idx: $student_idx})-[:ASSIGNED]->(:RegistrationTurn)<-[:HAS_TURN]-(reg:Registration {id: $registration_id})
RETURN reg.id AS id

// 2. Open groups of the subject
MATCH (st:Student {idx: $student_idx})
MATCH (reg:Registration {id: $registration_id})-[:OPENS]->(g:Group)
MATCH (g)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(:SubjectInstance)-[:INSTANCE_OF]->(:Subject {code: $subject_code})
OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
OPTIONAL MATCH (t:Teacher)-[:TEACHES]->(g)
OPTIONAL MATCH (st)-[mine:REGISTERED_IN]->(g)
RETURN
  g.id AS id,
  gt.g_type AS g_type,
  g.number AS number,
  g.weekday AS weekday,
  g.start_hr AS start,
  g.end_time AS end,
  g.capacity AS capacity,
  size([(g)<-[:REGISTERED_IN]-() | 1]) AS filled,
  r.building + " " + r.room_num AS room,
  t.name + " " + t.surname AS teacher,
  mine IS NOT NULL AS registered
ORDER BY gt.g_type, g.number
```

---

## POST /me/registrations/register

**Allowed:** Student, only for groups opened by a registration they have a turn in

**Request**

```json
{
	"subject_code": String,
	"group_id": String
}
```

**Response**

```json
{
	"ok": Boolean,
	"err": String?
}
```

Rejected when the student has no access to the group (`"Forbidden"`), already has another group of the same type for this subject in the same cycle, or the group is full. Registering again in a group the student is already in succeeds without changes.

**Query**

All checks and the write run in one query. It takes write locks on the student and then on the group (always in this order, so concurrent requests cannot deadlock). The student lock makes the student's concurrent requests wait, so they cannot end up in two groups of the same type; the group lock makes concurrent registrations to the group run one at a time, so they cannot both take the last place. No row means no access. Otherwise `status` is `ok`, `conflict` or `full`.

```cypher
MATCH (st:Student {idx: $student_idx})-[:ASSIGNED]->(:RegistrationTurn)<-[:HAS_TURN]-(:Registration)-[:OPENS]->(g:Group {id: $group_id})
MATCH (g)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(:SubjectInstance)-[:INSTANCE_OF]->(:Subject {code: $subject_code})
WITH DISTINCT st, g, gt
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
  WHEN already THEN "ok"
  WHEN conflict THEN "conflict"
  WHEN full THEN "full"
  ELSE "ok"
END AS status
FOREACH (_ IN CASE WHEN status = "ok" THEN [1] ELSE [] END |
  MERGE (st)-[r:REGISTERED_IN]->(g)
    ON CREATE SET r.registered_at = datetime()
)
RETURN status
```

---

## POST /me/registrations/deregister

**Allowed:** Student, only while a registration they have a turn in still opens the group

**Request**

```json
{
	"subject_code": String,
	"group_id": String
}
```

**Response**

```json
{
	"ok": Boolean,
	"err": String?
}
```

**Query**

```cypher
MATCH (st:Student {idx: $student_idx})-[r:REGISTERED_IN]->(g:Group {id: $group_id})
MATCH (g)-[:OF_TYPE]->(:GroupType)<-[:HAS_TYPE]-(:SubjectInstance)-[:INSTANCE_OF]->(:Subject {code: $subject_code})
MATCH (st)-[:ASSIGNED]->(:RegistrationTurn)<-[:HAS_TURN]-(:Registration)-[:OPENS]->(g)
DELETE r
RETURN g.id AS group_id
```

---

## GET /me/enrolments

**Allowed:** Student

**Request**

None.

**Response**

```json
{
	"enrolments": List[Enrolment]

	Enrolment = {
		"programme_id": String,
		"programme": String,
		"curriculum_id": String,
		"intake_year": String,
		"term_id": String,
		"sem": Integer,
		"cycle_id": String?,
		"year": String?,
		"season": String?
	}
}
```

**Query**

```cypher
MATCH (st:Student {idx: $student_idx})-[:ENROLLED]->(ct:CurriculumTerm)<-[:HAS_TERM]-(c:Curriculum)<-[:HAS_CURRICULUM]-(p:Programme)
OPTIONAL MATCH (ct)-[:TAUGHT_IN]->(ac:AcademicCycle)
RETURN
  p.id AS programme_id,
  p.name AS programme,
  c.id AS curriculum_id,
  c.intake_year AS intake_year,
  ct.id AS term_id,
  ct.sem AS sem,
  ac.id AS cycle_id,
  ac.year AS year,
  ac.season AS season
ORDER BY p.name, ct.sem
```

---

## GET /me/academic-cycles

**Allowed:** Student

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
MATCH (st:Student {idx: $student_idx})-[:ENROLLED]->(:CurriculumTerm)-[:TAUGHT_IN]->(ac:AcademicCycle)
RETURN DISTINCT ac.id AS id, ac.year AS year, ac.season AS season
```

---

## POST /me/academic-cycles/detail

**Allowed:** Student, only for cycles they are enrolled in (403 otherwise)

**Request**

```json
{
	"cycle_id": String
}
```

**Response**

```json
{
	"id": String,
	"year": String,
	"season": String,
	"subjects": List[CycleSubject]

	CycleSubject = {
		"code": String,
		"name": String,
		"ects": Integer?,
		"groups": List[CycleSubjectGroup]
	}

	CycleSubjectGroup = {
		"id": String,
		"g_type": String,
		"number": Integer,
		"weekday": Integer?,
		"start": Time?,
		"end": Time?,
		"room": String?,
		"teacher": String?,
		"grade": Float?
	}
}
```

`subjects` combines the subjects in the student's terms for that cycle with any other subjects they have groups in.

**Query**

```cypher
// 1. Cycle (also the access check)
MATCH (:Student {idx: $student_idx})-[:ENROLLED]->(:CurriculumTerm)-[:TAUGHT_IN]->(ac:AcademicCycle {id: $cycle_id})
RETURN ac.id AS id, ac.year AS year, ac.season AS season

// 2. Subjects in the student's terms for the cycle
MATCH (:Student {idx: $student_idx})-[:ENROLLED]->(ct:CurriculumTerm)-[:TAUGHT_IN]->(:AcademicCycle {id: $cycle_id})
MATCH (ct)-[:INCLUDES]->(su:Subject)
RETURN DISTINCT su.code AS code, su.name AS name, su.ects AS ects

// 3. The student's groups in the cycle
MATCH (st:Student {idx: $student_idx})-[reg:REGISTERED_IN]->(g:Group)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(si:SubjectInstance)
MATCH (si)-[:OFFERED_IN]->(:AcademicCycle {id: $cycle_id})
MATCH (si)-[:INSTANCE_OF]->(su:Subject)
OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
OPTIONAL MATCH (t:Teacher)-[:TEACHES]->(g)
RETURN
  su.code AS code,
  su.name AS name,
  su.ects AS ects,
  g.id AS id,
  gt.g_type AS g_type,
  g.number AS number,
  g.weekday AS weekday,
  g.start_hr AS start,
  g.end_time AS end,
  r.building + " " + r.room_num AS room,
  t.name + " " + t.surname AS teacher,
  reg.grade AS grade
ORDER BY su.name, gt.g_type, g.number
```

---

## GET /me/dashboard

**Allowed:** Student

**Request**

None.

**Response**

```json
{
	"groups": List[RegisteredGroup]

	RegisteredGroup = {
		"group_id": String,
		"course_code": String,
		"course_name": String,
		"g_type": String,
		"number": Integer,
		"weekday": Integer,
		"start": Time,
		"end": Time,
		"pnp": String,
		"room": String?,
		"cycle": String?,
		"cycle_start": Date?,
		"cycle_end": Date?,
		"teachers": List[{ "idx": String, "name": String, "surname": String }]
	}
}
```

**Query**

```cypher
MATCH (st:Student {idx: $student_idx})-[:REGISTERED_IN]->(g:Group)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(si:SubjectInstance)
MATCH (si)-[:INSTANCE_OF]->(su:Subject)
MATCH (si)-[:OFFERED_IN]->(ac:AcademicCycle)
OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
OPTIONAL MATCH (te:Teacher)-[:TEACHES]->(g)
WITH g, su, gt, ac, r, collect(DISTINCT te) AS teacher_nodes
RETURN
  g.id AS group_id,
  su.code AS course_code,
  su.name AS course_name,
  gt.g_type AS g_type,
  g.number AS number,
  g.weekday AS weekday,
  g.start_hr AS start,
  g.end_time AS end,
  g.pnp AS pnp,
  r.building + " " + r.room_num AS room,
  ac.year + " " + ac.season AS cycle,
  ac.start_date AS cycle_start,
  ac.end_date AS cycle_end,
  [x IN teacher_nodes WHERE x IS NOT NULL | {idx: x.idx, name: x.name, surname: x.surname}] AS teachers
```

---

## POST /opinions

**Allowed:** Student (about their own groups), Admin (on behalf of any student)

**Request**

```json
{
	"grade": Float,
	"content": String?,
	"submit": DateTime,
	"group_id": String,
	"teacher_idx": String,
	"student_idx": String?
}
```

`student_idx` is required for admins. For students it is ignored and taken from the token. `teacher_idx` must be a teacher who `TEACHES` the given group.

**Response**

```json
{
	"id": String?,
	"grade": Float,
	"content": String?,
	"submit": DateTime,
	"group_id": String,
	"teacher_idx": String,
	"err": String?
}
```

Fails with `"Forbidden"` if the student is not registered in the group, `"Teacher does not teach this group"` if `teacher_idx` is invalid for the group, or `"Opinion already exists"` if the student already submitted for that group and teacher.

**Query**

Validation, then the write. The duplicate check is repeated inside the write under a write lock on the student, so concurrent requests (e.g. a double click) create only one opinion; no row means a duplicate.

```cypher
MATCH (st:Student {idx: $student_idx})-[:REGISTERED_IN]->(g:Group {id: $group_id})
MATCH (t:Teacher {idx: $teacher_idx})-[:TEACHES]->(g)
SET st.idx = st.idx
WITH st, g, t
WHERE NOT EXISTS { (st)-[:WRITES]->(dup:Opinion)-[:ABOUT]->(g), (dup)-[:ABOUT_TEACHER]->(t) }
CREATE (o:Opinion {id: $id, grade: $grade, content: $content, submit: datetime($submit)})
CREATE (st)-[:WRITES]->(o)
CREATE (o)-[:ABOUT]->(g)
CREATE (o)-[:ABOUT_TEACHER]->(t)
RETURN o.id AS id, o.grade AS grade, o.content AS content, o.submit AS submit, g.id AS group_id, t.idx AS teacher_idx
```
