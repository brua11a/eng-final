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
MATCH (f:Faculty {id: $faculty_id})

CREATE (t:Teacher {
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
  t.idx AS idx,
  t.name AS name,
  t.surname AS surname,
  t.phone AS phone,
  t.degree AS degree,
  t.photo AS photo,
  t.working_since AS working_since,
  f.id AS faculty_id
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
MATCH (p:Programme {id: $programme})-[:HAS_CURRICULUM]->(c:Curriculum)-[:HAS_TERM]->(ct:CurriculumTerm {sem: 1})
WITH ct, c ORDER BY c.intake_year DESC LIMIT 1

CREATE (st:Student {
  idx: $idx,
  name: $name,
  surname: $surname,
  phone: $phone,
  joined: $joined,
  photo: $photo
})
CREATE (st)-[:ENROLLED]->(ct)

RETURN
  st.idx AS idx,
  st.name AS name,
  st.surname AS surname,
  st.phone AS phone,
  st.photo AS photo,
  st.joined AS joined
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

```cypher
MATCH (owner)
WHERE ($user_type = "Teacher" AND owner:Teacher {idx: $assigned_id})
   OR ($user_type = "Student" AND owner:Student {idx: $assigned_id})

SET
  owner:User,
  owner.email = $email,
  owner.passwd_hash = $passwd_hash

RETURN
  owner.email AS email,
  CASE
    WHEN owner:Teacher THEN "Teacher"
    WHEN owner:Student THEN "Student"
  END AS owner_type,
  owner.idx AS owner_idx
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
MATCH (st:Student {idx: $student_idx})
MATCH (g:Group {id: $group_id})

CREATE (o:Opinion {
  id: $id,
  grade: $grade,
  content: $content,
  submit: $submit
})
CREATE (st)-[:WRITES]->(o)
CREATE (o)-[:ABOUT]->(g)

RETURN
  o.id AS id,
  o.grade AS grade,
  o.content AS content,
  o.submit AS submit,
  g.id AS group_id
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
MATCH (su:Subject {code: $subject_code})
MATCH (r:Room {id: $room_id})

CREATE (g:Group {
  id: $id,
  weekday: $weekday,
  g_type: $g_type,
  number: $number,
  pnp: $pnp,
  capacity: $capacity,
  start_hr: $start_hr,
  end_time: $end_time
})-[:OF_SUBJECT]->(su),
(g)-[:IN_ROOM]->(r)

RETURN
  g.id AS id,
  g.weekday AS weekday,
  g.g_type AS g_type,
  g.number AS number,
  g.pnp AS pnp,
  g.capacity AS capacity,
  g.start_hr AS start_hr,
  g.end_time AS end_time,
  su.code AS subject_code,
  r.id AS room_id
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
CREATE (r:Room {
  id: $id,
  building: $building,
  room_num: $room_num
})

RETURN
  r.id AS id,
  r.building AS building,
  r.room_num AS room_num
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
CREATE (ac:AcademicCycle {
  id: $id,
  year: $year,
  season: $season
})

RETURN
  ac.id AS id,
  ac.year AS year,
  ac.season AS season
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
MERGE (su:Subject {code: $code})
  ON CREATE SET
    su.name = $name,
    su.ects = $ects
  ON MATCH SET
    su.name = $name,
    su.ects = $ects

RETURN
  su.code AS code,
  su.name AS name,
  su.ects AS ects
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
MATCH (c:Curriculum {id: $curriculum_id})
MATCH (ac:AcademicCycle {id: $cycle_id})

CREATE (ct:CurriculumTerm {id: $id, sem: $sem})
CREATE (c)-[:HAS_TERM]->(ct)
CREATE (ct)-[:TAUGHT_IN]->(ac)

RETURN
  ct.id AS id,
  ct.sem AS sem,
  c.id AS curriculum_id,
  ac.id AS cycle_id
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
MATCH (p:Programme {id: $programme_id})

CREATE (c:Curriculum {id: $id, intake_year: $intake_year})
CREATE (p)-[:HAS_CURRICULUM]->(c)

RETURN
  c.id AS id,
  p.id AS programme_id,
  c.intake_year AS intake_year
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
CREATE (fa:Faculty {
  id: $id,
  name: $name,
  full_name: $full_name
})

RETURN
  fa.id AS id,
  fa.name AS name,
  fa.full_name AS full_name
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
MATCH (st:Student {idx: $idx})
OPTIONAL MATCH (st)-[:ENROLLED]->(ct:CurriculumTerm)

RETURN
  st.idx AS idx,
  st.name AS name,
  st.surname AS surname,
  st.phone AS phone,
  st.photo AS photo,
  st.joined AS joined,
  st.avg_grade AS avg_grade,
  collect(DISTINCT ct.id) AS term_ids
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

```cypher
MATCH (ac:AcademicCycle {id: $cycle_id})
MATCH (fa:Faculty {id: $faculty_id})

CREATE (reg:Registration {id: $id, name: $name, reg_type: $reg_type})
CREATE (reg)-[:FOR_CYCLE]->(ac)
CREATE (reg)-[:FOR_FACULTY]->(fa)

RETURN reg.id AS id, reg.name AS name, reg.reg_type AS reg_type
```

```cypher
MATCH (reg:Registration {id: $registration_id})

CREATE (rt:RegistrationTurn {
  id: $turn_id,
  turn_number: $turn_number,
  date: date($date),
  start_hr: $start,
  end_time: $end
})
CREATE (reg)-[:HAS_TURN]->(rt)

RETURN rt.id AS id, rt.turn_number AS turn_number
```

```cypher
MATCH (reg:Registration {id: $registration_id})
MATCH (g:Group {id: $group_id})

MERGE (reg)-[:OPENS]->(g)
```
### (admin) List Faculties

```json
{}
```

```json
{
	"faculties": List[Faculty]
	
	Faculty = {
		"id": Integer,
		"name": String,
		"full_name": String
	}
}
```

```cypher
MATCH (fa:Faculty)
RETURN fa.id AS id, fa.name AS name, fa.full_name AS full_name
ORDER BY fa.name
```
### (admin) List Programmes

```json
{}
```

```json
{
	"programmes": List[Programme]
	
	Programme = {
		"id": Integer,
		"name": String,
		"faculty_id": Integer
	}
}
```

```cypher
MATCH (p:Programme)-[:OFFERED_BY]->(fa:Faculty)
RETURN p.id AS id, p.name AS name, fa.id AS faculty_id
ORDER BY p.name
```
### (admin) List Rooms

```json
{}
```

```json
{
	"rooms": List[Room]
	
	Room = {
		"id": Integer,
		"building": String,
		"room_num": String
	}
}
```

```cypher
MATCH (r:Room)
RETURN r.id AS id, r.building AS building, r.room_num AS room_num
ORDER BY r.building, r.room_num
```
### (admin) List Academic Cycles

```json
{}
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
MATCH (ac:AcademicCycle)
RETURN ac.id AS id, ac.year AS year, ac.season AS season
ORDER BY ac.year, ac.season
```

