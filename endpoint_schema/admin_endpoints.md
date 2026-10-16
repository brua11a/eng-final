### (admin) Create Teacher

```json
{
	"name": String,
	"surname": String,
	"phone": String,
	"degree": String,
	"photo": String?,
	"working_since": Date,
	"faculty_id": Integer
}
```

```json
{
	"idx": String,
	"name": String,
	"surname": String,
	"phone": String,
	"degree": String,
	"photo": String?,
	"working_since": Date,
	"faculty_id": Integer,
	"err": String?
}
```

```cypher
MATCH (i:Teacher)
WITH coalesce(max(toInteger(substring(i.idx, 1))), 0) AS last_num

MATCH (f:Faculty {id: 1})

MERGE (t:Teacher {
	name: "Adam",
	surname: "Wiktor",
	phone: "883 481 136"
})
  ON CREATE SET
    t.idx = "T" + (last_num + 1),
    t.degree = "dr inż.",
    t.working_since = date("2010-10-01"),
    t.photo = "photo"

MERGE (t)-[w:WORKS_AT]->(f)

RETURN t, w, f
```
### (admin) Create Student

```json
{
	"name": String,
	"surname": String,
	"phone": String,
	"photo": String?,
	"joined": ZonedDateTime,
	"programme": Integer
}
```

```json
{
	"idx": String,
	"name": String,
	"surname": String,
	"phone": String,
	"photo": String?,
	"joined": ZonedDateTime,
	"err": String?
}
```

```cypher
MATCH (i:Student)
WITH coalesce(max(toInteger(i.idx)), 0) AS last_num

MATCH (p:Programme {id: 1})-[ha:HAS_CURRICULUM]->(c:Curriculum)-[h:HAS_TERM]->(ct:CurriculumTerm {sem: 1})
WITH p, ha, last_num, ct, c, h ORDER BY c.intake_year DESC LIMIT 1

MERGE (st:Student {
    name: "Adam",
    surname: "Wiktor",
    phone: "883 481 2000"
})
  ON CREATE SET
    st.idx = toString(last_num + 1),
    st.joined = datetime(),
    st.photo = "photo"
MERGE (st)-[e:ENROLLED]->(ct)
RETURN st, e, ct, c, h, p, ha
```
### (admin) Assign User to account

```json
{
	"email": String,
	"passwd": String,
	"user_type": "Teacher" | "Student",
	"assigned_id": String
}
```

```json
{
	"email": String,
	"owner_type": "Teacher" | "Student",
	"owner_idx": String,
	"err": String?
}
```

### (student | admin) Create Opinion

```json
{
	"student_idx": String,
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
### (admin) Create Group

```json
{
	"weekday": Integer,
	"g_type": String,
	"number": Integer,
	"pnp": String,
	"capacity": Integer,
	"start_hr": ZonedTime,
	"end_time": ZonedTime,
	"subject_code": String,
	"room_id": Integer
}
```

```json
{
	"id": Integer,
	"weekday": Integer,
	"g_type": String,
	"number": Integer,
	"pnp": String,
	"capacity": Integer,
	"start_hr": ZonedTime,
	"end_time": ZonedTime,
	"subject_code": String,
	"room_id": Integer,
	"err": String?
}
```

```cypher
MATCH (su:Subject {code: "W04CBE-SI0401G"})
MATCH (r:Room {id: 14})
OPTIONAL MATCH (x:Group)

WITH su, r, coalesce(max(x.id), 0) + 1 AS new_id

CREATE (g:Group {
  id: new_id,
  weekday: 0,
  g_type: "W",
  number: 90,
  pnp: "ALL",
  capacity: 900,
  start_hr: time({hour: 7, minute: 0}),
  end_time: time({hour: 7, minute: 1})
})-[:OF_SUBJECT]->(su),
(g)-[:IN_ROOM]->(r)
RETURN g { .*, subject_code: su.code, room_id: r.id } AS group
```
### (admin) Create room

```json
{
	"building": String,
	"room_num": String
}
```

```json
{
	"id": Integer,
	"building": String,
	"room_num": String,
	"err": String?
}
```

```cypher
MERGE (r:Room {
  building: $building,
  room_num: $room_num
})
  ON CREATE SET r.id = $id
RETURN r
```
### (admin) Create AcademicCycle

```json
{
	"year": String,
	"season": String
}
```

```json
{
	"id": Integer,
	"year": String,
	"season": String,
	"err": String?
}
```

```cypher
MERGE (ac:AcademicCycle {
  year: "2025/2026",
  season: "Z"
})
  ON CREATE SET
    ac.id = 100

RETURN ac
```
### (admin) Create Subject

```json
{
	"code": String,
	"name": String,
	"ects": Integer?
}
```

```json
{
	"code": String,
	"name": String,
	"ects": Integer?,
	"err": String?
}
```

```cypher
MERGE (su:Subject {
  code: "W04-001",
})
  ON CREATE SET
    su.ects = 5,
    su.name = "Bazy danych"

RETURN su
```
### (admin) Create CurriculumTerm

```json
{
	"sem": Integer,
	"curriculum_id": Integer,
	"cycle_id": Integer
}
```

```json
{
	"id": Integer,
	"sem": Integer,
	"curriculum_id": Integer,
	"cycle_id": Integer,
	"err": String?
}
```

```cypher
MATCH (c:Curriculum {id: 1})
MATCH (ac:AcademicCycle {id: 1})

MERGE (c)-[:HAS_TERM]->(ct:CurriculumTerm {
  sem: 1
})
  ON CREATE SET
    ct.id = 100

MERGE (ct)-[:TAUGHT_IN]->(ac)

RETURN ct, c, ac
```
### (admin) Create Curriculum

```json
{
	"programme_id": Integer,
	"intake_year": String
}
```

```json
{
	"id": Integer,
	"programme_id": Integer,
	"intake_year": String,
	"err": String?
}
```

```cypher
MATCH (p:Programme {id: 1})

MERGE (p)-[:HAS_CURRICULUM]->(c:Curriculum {
  intake_year: "2025/26"
})
  ON CREATE SET
    c.id = 10

RETURN c, p
```
### (admin) Create Faculty

```json
{
	"name": String,
	"full_name": String
}
```

```json
{
	"id": Integer,
	"name": String,
	"full_name": String,
	"err": String?
}
```

```cypher
MERGE (fa:Faculty {
  name: "W4N",
  full_name: "Faculty of Fundamental Problems of Technology"
})
  ON CREATE SET
    fa.id = 1

RETURN fa
```
### (admin | teacher) Student detail

```json
{
	"idx": String
}
```

```json
{
	"idx": String,
	"name": String,
	"surname": String,
	"phone": String,
	"photo": String?,
	"joined": ZonedDateTime,
	"avg_grade": Float?,
	"term_ids": List[Integer],
	"err": String?
}
```

```cypher
MATCH (st:Student {idx: "279413"})
MATCH (st)-[e:ENROLLED]->(ct:CurriculumTerm)
RETURN st, e, ct
```
### (admin) Start registrations

```json
{
	"name": String,
	"cycle_id": Integer,
	"faculty_id": Integer,
	"reg_type": "zapisowa",
	"turns": List[RegistrationTurn],
	"group_ids": List[Integer]

	RegistrationTurn = {
		"turn_number": Integer,
		"date": Date,
		"start": Time,
		"end": Time
	}
}
```

```json
{
	"id": Integer,
	"name": String,
	"reg_type": "zapisowa",
	"turns": List[RegistrationTurn],
	"group_ids": List[Integer],
	"err": String?
}
```

