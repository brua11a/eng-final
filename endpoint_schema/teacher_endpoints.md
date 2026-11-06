# Teacher endpoints

See `user_endpoints.md` for conventions. Admins can use every endpoint here without restrictions. Teachers are limited to their own groups and the students in them. `$teacher_idx` is the caller's own idx, taken from the token.

---

## POST /students/detail

**Allowed:** Admin; Teacher, only for students registered in one of their groups (403 otherwise)

**Request**

```json
{
	"student_idx": String
}
```

**Response**

```json
{
	"idx": String,
	"name": String,
	"surname": String,
	"phone": String,
	"photo": String?,
	"joined": DateTime,
	"avg_grade": Float?,
	"term_ids": List[String],
	"err": String?
}
```

`avg_grade` is computed by the server (`average_grade` in `app/graph_backend/grades.py`) from the rows of query 3:

- An attempt is one subject in one cycle the student had groups in.
- An attempt is complete when every group type of the subject has a grade. Several graded groups of the same type are averaged.
- The attempt grade is the weighted average of its group-type grades, using the group-type weights.
- Each subject uses its latest complete attempt, so a passed retake replaces the earlier failed attempt.
- `avg_grade` is the ECTS-weighted average of those subject grades. It is null when no subject has a complete attempt.

**Query**

```cypher
// 1. Access check (teachers only)
MATCH (t:Teacher {idx: $teacher_idx})-[:TEACHES]->(:Group)<-[:REGISTERED_IN]-(st:Student {idx: $student_idx})
RETURN st.idx AS idx

// 2. Profile and terms
MATCH (st:Student {idx: $student_idx})
RETURN
  st.idx AS idx,
  st.name AS name,
  st.surname AS surname,
  st.phone AS phone,
  st.photo AS photo,
  st.joined AS joined,
  COLLECT { MATCH (st)-[:ENROLLED]->(ct:CurriculumTerm) RETURN ct.id } AS term_ids

// 3. Grade rows: every group type of every subject attempt, with the grade if any
MATCH (st:Student {idx: $student_idx})-[:REGISTERED_IN]->(attended:Group)-[:OF_TYPE]->(:GroupType)<-[:HAS_TYPE]-(su:Subject)
MATCH (attended)-[:IN_CYCLE]->(ac:AcademicCycle)
WITH DISTINCT st, su, ac
MATCH (su)-[:HAS_TYPE]->(gt:GroupType)
OPTIONAL MATCH (st)-[r:REGISTERED_IN]->(g:Group)-[:OF_TYPE]->(gt)
WHERE (g)-[:IN_CYCLE]->(ac)
RETURN
  su.code AS subject,
  su.ects AS ects,
  ac.year AS year,
  ac.season AS season,
  gt.id AS type,
  gt.weight AS weight,
  r.grade AS grade
```

---

## GET /me/groups

**Allowed:** Teacher (own groups); Admin (any teacher's groups, `teacher_idx` required)

**Request**

Query string:

```json
{
	"teacher_idx": String?
}
```

`teacher_idx` is only used for admins. Teachers always get their own groups.

**Response**

```json
{
	"groups": List[TeachingGroup]

	TeachingGroup = {
		"group_id": String,
		"course_code": String,
		"course_name": String,
		"g_type": String,
		"group_num": Integer,
		"academic_cycle": String,
		"room": String,
		"weekday": Integer,
		"start": Time?,
		"end": Time?,
		"pnp": String
	}
}
```

**Query**

```cypher
MATCH (t:Teacher {idx: $idx})-[:TEACHES]->(g:Group)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(su:Subject)
OPTIONAL MATCH (g)-[:IN_CYCLE]->(ac:AcademicCycle)
OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
RETURN
  g.id AS group_id,
  su.code AS course_code,
  su.name AS course_name,
  gt.g_type AS g_type,
  g.number AS group_num,
  g.weekday AS weekday,
  g.start_hr AS start,
  g.end_time AS end,
  g.pnp AS pnp,
  ac.year AS cycle_year,
  ac.season AS cycle_season,
  r.building AS building,
  r.room_num AS room_num
ORDER BY ac.year DESC, ac.season, su.name, gt.g_type, g.number
```

---

## POST /groups/students

**Allowed:** Admin; Teacher, only for groups they teach (403 otherwise)

**Request**

```json
{
	"group_id": String
}
```

**Response**

```json
{
	"students": List[StudentInGroup]

	StudentInGroup = {
		"idx": String,
		"name": String,
		"surname": String,
		"phone": String,
		"photo": String?,
		"joined": DateTime,
		"grade": Float?
	}
}
```

**Query**

```cypher
// 1. Access check (teachers only)
MATCH (t:Teacher {idx: $teacher_idx})-[:TEACHES]->(g:Group {id: $group_id})
RETURN g.id AS id

// 2. Students in the group
MATCH (g:Group {id: $group_id})
MATCH (st:Student)-[r:REGISTERED_IN]->(g)
RETURN
  st.idx AS idx,
  st.name AS name,
  st.surname AS surname,
  st.phone AS phone,
  st.photo AS photo,
  st.joined AS joined,
  r.grade AS grade
ORDER BY st.surname, st.name
```

---

## POST /groups/students/grade

**Allowed:** Admin; Teacher, only for groups they teach (403 otherwise)

**Request**

```json
{
	"group_id": String,
	"student_idx": String,
	"grade": Float
}
```

**Response**

```json
{
	"group_id": String,
	"student_idx": String,
	"grade": Float,
	"err": String?
}
```

**Query**

```cypher
// 1. Access check (teachers only)
MATCH (t:Teacher {idx: $teacher_idx})-[:TEACHES]->(g:Group {id: $group_id})
RETURN g.id AS id

// 2. Set the grade
MATCH (st:Student {idx: $student_idx})-[r:REGISTERED_IN]->(g:Group {id: $group_id})
SET r.grade = $grade
RETURN g.id AS group_id, st.idx AS student_idx, r.grade AS grade
```
