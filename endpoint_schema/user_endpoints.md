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
	"err": String?
}
```

```cypher
MATCH (u:User {email: "adam@example.com"})
RETURN
  u.email AS email,
  u.passwd_hash AS passwd_hash,
  u:Student AS is_student,
  u:Teacher AS is_teacher,
  u.idx AS idx
```
### (user) Teacher catalogue

```json
{}
```

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

```json
{
	"name": String
}
```

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
MATCH (t:Teacher)-[:WORKS_AT]->(fa:Faculty)
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

```json
{}
```

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
		"id": Integer,
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

```json
{
	"name": String?,
	"code": String?
}
```

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
		"id": Integer,
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

RETURN
  su.code AS code,
  su.name AS name,
  su.ects AS ects,
  COLLECT {
    MATCH (g:Group)-[:OF_SUBJECT]->(su)
    OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
    OPTIONAL MATCH (:Registration)-[:OPENS]->(g)
    OPTIONAL MATCH (reg:Registration)-[:OPENS]->(g)
    OPTIONAL MATCH (reg)-[:FOR_CYCLE]->(ac:AcademicCycle)
    WITH g, r, ac
    ORDER BY g.g_type, g.number, g.weekday, g.start_hr
    RETURN {
      id: g.id,
      weekday: g.weekday,
      g_type: g.g_type,
      number: g.number,
      pnp: g.pnp,
      capacity: g.capacity,
      start_hr: g.start_hr,
      end_time: g.end_time,
      cycle: ac.year + " " + ac.season,
      room: r.building + " " + r.room_num
    }
  } AS groups

ORDER BY su.name
```
### (user) Curriculum catalogue

```json
{}
```

```json
{
	curricula: List[Curriculum]
	
	Curriculum = {
		"id": Integer,
		"programme_id": Integer,
		"name": String,
		"intake_year": String
	}
}
```

```json
{
	"name": String,
}
```

```json
{
	curricula: List[Curriculum]
	
	Curriculum = {
		"id": Integer,
		"programme_id": Integer,
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
MATCH (s:Subject {code: "W04CBE-SI0403G"})<-[a:OF_SUBJECT]-(b:Group)<-[c:TEACHES]-(t:Teacher)

RETURN
  s.name AS name,
  s.ects AS ects,
  collect(DISTINCT {
    id: t.idx,
    name: t.name + " " + t.surname
  }) AS taught_by
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
		"id": Integer,
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
MATCH (su:Subject {code: "W04CBE-SI0403G"})

RETURN
  su.name AS name,
  COLLECT {
    MATCH (g:Group)-[:OF_SUBJECT]->(su)
    WITH DISTINCT su, g.g_type AS g_type
    ORDER BY g_type
    RETURN {
      g_type: g_type,
      groups: COLLECT {
        MATCH (g:Group {g_type: g_type})-[:OF_SUBJECT]->(su)
        OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
        OPTIONAL MATCH (reg:Registration)-[:OPENS]->(g)
        OPTIONAL MATCH (reg)-[:FOR_CYCLE]->(ac:AcademicCycle)
        WITH DISTINCT g, r, ac
        ORDER BY g.weekday, g.start_hr, g.number
        RETURN {
          id: g.id,
          weekday: g.weekday,
          number: g.number,
          pnp: g.pnp,
          capacity: g.capacity,
          start_hr: g.start_hr,
          end_hr: g.end_time,
          cycle: ac.year + " " + ac.season,
          room: r.building + " " + r.room_num,
          filled: COUNT { (:Student)-[:REGISTERED_IN]->(g) }
        }
      }
    }
  } AS groups_by_type
```
### (user) Group detail

```json
{
	"code": String,
	"group_num": Integer,
	"g_type": String
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
MATCH (su:Subject {code: "W04CBE-SI0403G"})<-[:OF_SUBJECT]-(g:Group {number: 1, g_type: "C"})
OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)

WITH su, g, r,
  date() + duration({days: (g.weekday - date().dayOfWeek + 7) % 7}) AS first_date

RETURN
  su.name AS course_name,
  g.g_type AS g_type,
  head(COLLECT {
    MATCH (:Registration)-[:OPENS]->(g)
    MATCH (:Registration)-[:FOR_CYCLE]->(ac:AcademicCycle)
    RETURN ac.year + " " + ac.season
  }) AS academic_cycle,
  g.number AS group_num,
  r.building AS building,
  [d IN [w IN range(0, 4) | first_date + duration({days: 7 * w})]
   WHERE datetime({date: d, time: g.end_time}) > datetime() |
   {
     class_date: d,
     class_start: g.start_hr,
     class_end: g.end_time,
     building: r.building
   }
  ][..4] AS nearest_classes,
  COUNT { (:Student)-[:REGISTERED_IN]->(g) } AS filled,
  g.capacity AS capacity,
  head(COLLECT {
    MATCH (t:Teacher)-[:TEACHES]->(g)
    RETURN {id: t.idx, name: t.name + " " + t.surname}
  }) AS teacher
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
MATCH (n:Teacher {idx: "T001"})

RETURN
  n.degree AS degree,
  n.name + " " + n.surname AS name,
  n.email AS email,
  n.phone AS phone,
  COLLECT {
    MATCH (n)-[:TEACHES]->(g:Group)-[:OF_SUBJECT]->(su:Subject)
    WITH su, g
    ORDER BY g.g_type, g.number
    WITH su, collect({
      id: g.id,
      g_type: g.g_type,
      number: g.number,
      weekday: g.weekday,
      start_hr: g.start_hr,
      end_time: g.end_time
    }) AS groups
    ORDER BY su.name
    RETURN {
      code: su.code,
      name: su.name,
      groups: groups
    }
  } AS courses
```
### (user) Dashboard

```json
{} %%derive from session%%
```

```json
{
	"groups": List[GroupInList],
	"index": Integer,
	"this_week": Callendar,
	"next_week": Callendar
	
	GroupInList = {
		"cycle": String,
		"name": String,
		"course_code": String,
		"groups": List[GroupLite],
		
	}
	
	GroupLite = {
		"g_type": String,
		"number": Integer
	}
	
	Callendar = {
		%%zostawie to na koniec%%
	}
}
```