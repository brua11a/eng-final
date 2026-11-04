### (user) Login
```json
{   
    "email": String,
    "password": String
}
```

```json
{
	"ok": Boolean,
	"err": String?,
	"email": String?,
	"idx": String?,
	"roles": List["Admin" | "Teacher" | "Student"]?,
	"token": String?
}
```

```cypher
MATCH (u:User {email: $email})
RETURN
  u.email AS email,
  u.passwd_hash AS passwd_hash,
  u.idx AS idx,
  u:Inactive AS inactive,
  u:Admin AS admin,
  u:Teacher AS teacher,
  u:Student AS student
```

If `inactive` is true, return `ok: false` and `err: "Account inactive"` without a token. Every `User` is also a `Person`. The token carries every role label on that account: `Admin`, `Teacher`, and `Student` can all be present.
### (user) Teacher catalogue

`GET /teachers` — query: `name` (optional String), substring match on full name.

```json
{
	teachers: List[Teacher]
	
	Teacher = {
		"idx": String,
		"name": String,
		"surname": String,
		"phone": String,
		"degree": String,
		"photo": String?,
		"working_since": Date,
		"faculty": String
	}
}
```

```cypher
MATCH (t:Teacher)
OPTIONAL MATCH (t)-[:WORKS_AT]->(fa:Faculty)
WHERE $name IS NULL
   OR toLower(t.name + " " + t.surname) CONTAINS toLower($name)

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
```

### (user) Subject catalogue

`GET /subjects` — query: `name`, `code` (optional String), substring match.

```json
{
	subject_and_groups: List[SubjectAndGroup]
	
	SubjectAndGroup = {
		"code": String,
		"name": String,
		"ects": Integer?,
		"groups": List[Group]
	}
	
	Group = {
		"id": String,
		"weekday": Integer,
		"g_type": String,
		"number": Integer,
		"pnp": String,
		"capacity": Integer,
		"start_hr": ZonedTime,
		"end_time": ZonedTime,
		"cycle": String,
		"room": String
	}
}
```

```cypher
MATCH (su:Subject)
WHERE ($name IS NULL OR toLower(su.name) CONTAINS toLower($name))
  AND ($code IS NULL OR toLower(su.code) CONTAINS toLower($code))
OPTIONAL MATCH (g:Group)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(su)
OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
OPTIONAL MATCH (reg:Registration)-[:OPENS]->(g)
OPTIONAL MATCH (reg)-[:FOR_CYCLE]->(ac:AcademicCycle)

RETURN
  su.code AS subject_code,
  su.name AS subject_name,
  su.ects AS ects,
  g.id AS group_id,
  g.weekday AS weekday,
  gt.g_type AS g_type,
  g.number AS number,
  g.pnp AS pnp,
  g.capacity AS capacity,
  g.start_hr AS start_hr,
  g.end_time AS end_time,
  r.building AS building,
  r.room_num AS room_num,
  ac.year AS cycle_year,
  ac.season AS cycle_season

ORDER BY su.name, gt.g_type, g.number
```
### (user) Curriculum catalogue

`GET /curricula` — query: `name` (optional String), substring match on programme name.

```json
{
	curricula: List[Curriculum]
	
	Curriculum = {
		"id": String,
		"programme_id": String,
		"name": String,
		"intake_year": String
	}
}
```

```cypher
MATCH (p:Programme)-[:HAS_CURRICULUM]->(c:Curriculum)
WHERE ($name IS NULL OR toLower(p.name) CONTAINS toLower($name))

RETURN
  c.id AS id,
  p.id AS programme_id,
  p.name AS name,
  c.intake_year AS intake_year

ORDER BY p.name, c.intake_year DESC
```
### (user) Subject detail

```json
{
	"code": String
}
```

```json
{
	"name": String,
	"ects": Integer?,
	"taught_by": List[TeacherName]
	
	TeacherName = {
		"id": String,
		"name": String
	}
}
```

```cypher
MATCH (s:Subject {code: $code})
OPTIONAL MATCH (s)-[:HAS_TYPE]->(:GroupType)<-[:OF_TYPE]-(:Group)<-[:TEACHES]-(t:Teacher)

RETURN
  s.name AS name,
  s.ects AS ects,
  t.idx AS teacher_idx,
  t.name AS teacher_name,
  t.surname AS teacher_surname
```
### (user) List Subject groups

```json
{
	"code": String
}
```

```json
{
	"name": String,
	"groups": List[Group]
	
	GroupTracked = {
		"id": String,
		"weekday": Integer,
		"g_type": String,
		"number": Integer,
		"pnp": String,
		"capacity": Integer,
		"start_hr": ZonedTime,
		"end_time": ZonedTime,
		"cycle": String,
		"room": String,
		"filled": Integer
	}
}
```

```cypher
MATCH (su:Subject {code: $code})-[:HAS_TYPE]->(gt:GroupType)<-[:OF_TYPE]-(g:Group)
OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
OPTIONAL MATCH (reg:Registration)-[:OPENS]->(g)
OPTIONAL MATCH (reg)-[:FOR_CYCLE]->(ac:AcademicCycle)
OPTIONAL MATCH (st:Student)-[:REGISTERED_IN]->(g)

RETURN
  su.name AS subject_name,
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
  ac.year AS cycle_year,
  ac.season AS cycle_season,
  count(st) AS filled

ORDER BY gt.g_type, g.weekday, g.start_hr, g.number
```
### (user) Group detail

```json
{
	"group_id": String
}
```

```json
{
	"course_name": String,
	"g_type": String,
	"academic_cycle": String,
	"group_num": Integer,
	"building": String,
	"nearest_classes": List[Classes],
	"filled": Integer,
	"capacity": Integer,
	"teacher": TeacherName
	
	Classes = {
		"class_date": Date,
		"class_start": Time,
		"class_end": Time,
		"building": String
	}
	
	TeacherName = {
		"id": String,
		"name": String
	}
}
```

```cypher
MATCH (g:Group {id: $group_id})-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(su:Subject)
OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
OPTIONAL MATCH (reg:Registration)-[:OPENS]->(g)
OPTIONAL MATCH (reg)-[:FOR_CYCLE]->(ac:AcademicCycle)
OPTIONAL MATCH (t:Teacher)-[:TEACHES]->(g)
OPTIONAL MATCH (st:Student)-[:REGISTERED_IN]->(g)

RETURN
  su.name AS course_name,
  gt.g_type AS g_type,
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
```
### (user) Teacher detail

```json
{
	"idx": String
}
```

```json
{
	"degree": String,
	"name": String,
	"phone": String,
	"email": String?,
	"groups": List[GroupAndCourse]
	
	GroupAndCourse = {
		"course_code": String,
		"g_type": String,
		"group_num": Integer
	}
}
```

```cypher
MATCH (t:Teacher {idx: $idx})
OPTIONAL MATCH (t)-[:TEACHES]->(g:Group)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(su:Subject)

RETURN
  t.degree AS degree,
  t.name AS name,
  t.surname AS surname,
  t.email AS email,
  t.phone AS phone,
  su.code AS course_code,
  gt.g_type AS g_type,
  g.number AS group_num
```
### (user) Dashboard

```json
{} %%derive from session%%
```

```json
{
	"groups": List[RegisteredGroup]
	
	RegisteredGroup = {
		"course_code": String,
		"course_name": String,
		"g_type": String,
		"number": Integer,
		"weekday": Integer,
		"start": ZonedTime,
		"end": ZonedTime,
		"room": String?,
		"cycle": String?
	}
}
```

```cypher
MATCH (st:Student {idx: $student_idx})-[:REGISTERED_IN]->(g:Group)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(su:Subject)
OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
OPTIONAL MATCH (reg:Registration)-[:OPENS]->(g)
OPTIONAL MATCH (reg)-[:FOR_CYCLE]->(ac:AcademicCycle)

RETURN
  su.code AS course_code,
  su.name AS course_name,
  gt.g_type AS g_type,
  g.number AS number,
  g.weekday AS weekday,
  g.start_hr AS start,
  g.end_time AS end,
  r.building + " " + r.room_num AS room,
  ac.year + " " + ac.season AS cycle
```