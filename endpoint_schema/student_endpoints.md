### (student | admin) Create Opinion

```json
{
	"grade": Float,
	"content": String?,
	"submit": ZonedDateTime,
	"group_id": Integer
}
```

```json
{
	"id": Integer,
	"grade": Float,
	"content": String?,
	"submit": ZonedDateTime,
	"group_id": Integer,
	"err": String?
}
```

```cypher
MATCH (st:Student {idx: $student_idx})
MATCH (g:Group {id: $group_id})

CREATE (o:Opinion {id: $id, grade: $grade, content: $content, submit: $submit})
CREATE (st)-[:WRITES]->(o)
CREATE (o)-[:ABOUT]->(g)

RETURN o.id AS id, o.grade AS grade, o.content AS content, o.submit AS submit, g.id AS group_id
```
### (student) Show registrations

```json
{} %%derive from session%%
```

```json
{
	available_registrations: List[Registrations]
	
	Registrations = {
		"id": Integer,
		"name": String,
		"reg_type": "zapisowa",
		"curriculum_id": Integer,
		"turn_number": Integer,
		"date": Date,
		"start": Time,
		"end": Time
	}
}
```

```cypher
MATCH (st:Student {idx: $student_idx})-[:ASSIGNED]->(tu:TurnAssignment)-[:FOR_TURN]->(rt:RegistrationTurn)
MATCH (tu)-[:FOR_CURRICULUM]->(c:Curriculum)
MATCH (reg:Registration)-[:HAS_TURN]->(rt)

RETURN
  reg.id AS id,
  reg.name AS name,
  reg.reg_type AS reg_type,
  c.id AS curriculum_id,
  rt.turn_number AS turn_number,
  rt.date AS date,
  rt.start_hr AS start,
  rt.end_time AS end
```
### (student) Show courses in registration


```json
{
	"registration_id": Integer
}
```

```json
{
	"courses": List[Course]
	
	Course = {
		"id": String, 
		"name": String,
		"classes": List[Class],
		"academic_cycle": String
	}
	
	Class = {
		"g_type": String,
		"count": Integer
	}
}
```

```cypher
MATCH (reg:Registration {id: $registration_id})-[:FOR_CYCLE]->(ac:AcademicCycle)
MATCH (reg)-[:OPENS]->(g:Group)-[:OF_SUBJECT]->(su:Subject)

RETURN
  su.code AS subject_code,
  su.name AS subject_name,
  g.g_type AS g_type,
  g.id AS group_id,
  ac.year AS cycle_year,
  ac.season AS cycle_season
```
### (student) Register to Group

```json
{
	"course_id": String,
	"group_id": Integer
}
```

```json
{
	"ok": Boolean,
	"err": String?
}
```

```cypher
MATCH (st:Student {idx: $student_idx})
MATCH (g:Group {id: $group_id})-[:OF_SUBJECT]->(su:Subject {code: $course_id})

MERGE (st)-[r:REGISTERED_IN]->(g)
  ON CREATE SET r.registered_at = datetime()

RETURN g.id AS group_id, su.code AS course_id, r.registered_at AS registered_at
```
### (student) Show groups in registration

```json
{
	"registration_id": Integer,
	"course_id": String
}
```

```json
{
	"groups": List[OpenGroup]
	
	OpenGroup = {
		"id": Integer,
		"g_type": String,
		"number": Integer,
		"weekday": Integer,
		"start": ZonedTime,
		"end": ZonedTime,
		"capacity": Integer,
		"filled": Integer,
		"room": String?,
		"teacher": String?,
		"registered": Boolean
	}
}
```

```cypher
MATCH (st:Student {idx: $student_idx})
MATCH (reg:Registration {id: $registration_id})-[:OPENS]->(g:Group)-[:OF_SUBJECT]->(:Subject {code: $course_id})
OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
OPTIONAL MATCH (t:Teacher)-[:TEACHES]->(g)
OPTIONAL MATCH (st)-[mine:REGISTERED_IN]->(g)

RETURN
  g.id AS id,
  g.g_type AS g_type,
  g.number AS number,
  g.weekday AS weekday,
  g.start_hr AS start,
  g.end_time AS end,
  g.capacity AS capacity,
  size([(g)<-[:REGISTERED_IN]-() | 1]) AS filled,
  r.building + " " + r.room_num AS room,
  t.name + " " + t.surname AS teacher,
  mine IS NOT NULL AS registered
ORDER BY g.g_type, g.number
```
### (student) My enrolments

```json
{} %%derive from session%%
```

```json
{
	"enrolments": List[Enrolment]
	
	Enrolment = {
		"programme_id": Integer,
		"programme": String,
		"curriculum_id": Integer,
		"intake_year": String,
		"term_id": Integer,
		"sem": Integer,
		"cycle_id": Integer?,
		"year": String?,
		"season": String?
	}
}
```

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
### (student) List my Academic Cycles

```json
{} %%derive from session%%
```

```json
{
	"cycles": List[AcademicCycle]
	
	AcademicCycle = {
		"id": Integer,
		"year": String,
		"season": String
	}
}
```

```cypher
MATCH (st:Student {idx: $student_idx})-[:ENROLLED]->(:CurriculumTerm)-[:TAUGHT_IN]->(ac:AcademicCycle)

RETURN DISTINCT ac.id AS id, ac.year AS year, ac.season AS season
```
### (student) My Academic Cycle detail

```json
{
	"cycle_id": Integer
}
```

```json
{
	"id": Integer,
	"year": String,
	"season": String
}
```

```cypher
MATCH (:Student {idx: $student_idx})-[:ENROLLED]->(:CurriculumTerm)-[:TAUGHT_IN]->(ac:AcademicCycle {id: $cycle_id})

RETURN ac.id AS id, ac.year AS year, ac.season AS season
```
