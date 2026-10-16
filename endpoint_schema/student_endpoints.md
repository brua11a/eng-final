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
MATCH (st:Student {idx: "279413"})
MATCH (g:Group {id: 6032})
OPTIONAL MATCH (x:Opinion)
WITH st, g, coalesce(max(x.id), 0) + 1 AS new_id

MERGE (st)-[w:WRITES]->(o:Opinion)-[a:ABOUT]->(g)
  ON CREATE SET
    o.id = new_id,
    o.grade = 4.0,
    o.content = "bylo OK",
    o.submit = datetime()

RETURN g,o,st,w,a
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
MATCH (st:Student {idx: "279413"})-[:ASSIGNED]->(tu:TurnAssignment)-[:FOR_TURN]->(rt:RegistrationTurn)
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

ORDER BY rt.date, rt.start_hr
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
MATCH (n:RegistrationTurn {id: 7})<-[r:HAS_TURN]-(reg:Registration)
MATCH (reg)-[op:OPENS]->(gr:Group)

RETURN reg, op, gr;
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
MATCH (st:Student {idx: "279413"})
MATCH (g:Group {id: 6011})-[:OF_SUBJECT]->(su:Subject {code: "W04CBE-SI0403G"})
OPTIONAL MATCH (:Student)-[taken:REGISTERED_IN]->(g)
WITH st, g, su, count(taken) AS taken_seats

WHERE EXISTS { (st)-[:REGISTERED_IN]->(g) }
   OR taken_seats < g.capacity

MERGE (st)-[r:REGISTERED_IN]->(g)
  ON CREATE SET
    r.registered_at = datetime()

RETURN st, r, g, su
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
