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

`GET /subjects` — query: `name`, `code` (optional String), substring match on **template** subject code/name.

```json
{
	"cycle_columns": List[String],
	"subjects": List[SubjectCatalogueItem]

	SubjectCatalogueItem = {
		"code": String,
		"name": String,
		"ects": Integer?,
		"faculty": String,
		"catalogue_code": String,
		"cycles": List[SubjectCycleCell]
	}

	SubjectCycleCell = {
		"instance_id": String?,
		"group_count": Integer,
		"registration_open": Boolean
	}
}
```

Rows are **one per template subject**; `cycles` aligns with `cycle_columns` (e.g. `2025/26-Z`) and describes **SubjectInstance** offerings.

```cypher
MATCH (su:Subject)
WHERE ($name IS NULL OR toLower(su.name) CONTAINS toLower($name))
  AND ($code IS NULL OR toLower(su.code) CONTAINS toLower($code))
OPTIONAL MATCH (su)<-[:INCLUDES]-(:CurriculumTerm)<-[:HAS_TERM]-(:Curriculum)<-[:HAS_CURRICULUM]-(:Programme)-[:OFFERED_BY]->(fa:Faculty)
WITH su, collect(DISTINCT fa.name) AS faculty_names
OPTIONAL MATCH (su)<-[:INSTANCE_OF]-(si:SubjectInstance)-[:OFFERED_IN]->(ac:AcademicCycle)
OPTIONAL MATCH (si)-[:HAS_GROUP]->(g:Group)
OPTIONAL MATCH (reg:Registration)-[:FOR_CYCLE]->(ac)
OPTIONAL MATCH (reg)-[:OPENS]->(g)
RETURN su.code, su.name, su.ects, faculty_names, si.id, si.catalogue_code,
  ac.id, ac.year, ac.season, count(DISTINCT g), count(DISTINCT reg) > 0
ORDER BY su.name, ac.year, ac.season
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
### (user) Organizational units catalogue

`GET /organizational-units` — query: `name` (optional String), substring match on short or full name.

```json
{
	"faculties": List[Faculty]

	Faculty = {
		"id": String,
		"name": String,
		"full_name": String
	}
}
```

```cypher
MATCH (fa:Faculty)
WHERE $name IS NULL
   OR toLower(fa.name) CONTAINS toLower($name)
   OR toLower(fa.full_name) CONTAINS toLower($name)
RETURN fa.id AS id, fa.name AS name, fa.full_name AS full_name
ORDER BY fa.name
```
### (user) Subject detail

```json
{
	"code": String
}
```

```json
{
	"code": String,
	"name": String,
	"ects": Integer?,
	"taught_by": List[TeacherName],
	"instances": List[SubjectInstanceItem]

	SubjectInstanceItem = {
		"id": String,
		"cycle": String,
		"catalogue_code": String,
		"group_count": Integer
	}
}
```
### (user) List Subject groups

`POST /subjects/groups` — body: `{ "instance_id": String }` (SubjectInstance id).

```json
{
	"name": String,
	"instance_id": String,
	"cycle": String,
	"groups": List[GroupTracked]
}
```

```cypher
MATCH (si:SubjectInstance {id: $instance_id})-[:INSTANCE_OF]->(su:Subject)
MATCH (si)-[:OFFERED_IN]->(ac:AcademicCycle)
MATCH (si)-[:HAS_GROUP]->(g:Group)-[:OF_TYPE]->(gt:GroupType)
...
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