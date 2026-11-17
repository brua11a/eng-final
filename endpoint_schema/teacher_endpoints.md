# Teacher endpoints

See `user_endpoints.md` for conventions. Admins can use every endpoint here without restrictions. Teachers are limited to their own groups and the students in them. `$teacher_idx` is the caller's own idx, taken from the token.

---

## GET /students/{student_idx}

**Allowed:** Admin; Teacher, only for students registered in one of their groups (403 otherwise)

**Request**

No body; parameters go in the URL:

```http
GET /students/2794131
```

- `student_idx` (path): student idx.

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
	"term_ids": List[String]
}
```

`avg_grade` is computed by the server (`average_grade` in `app/graph_backend/grades.py`) from the rows of query 3:

- An attempt is one subject in one cycle the student had groups in.
- An attempt is complete when every group type of the subject has a grade. Several graded groups of the same type are averaged.
- The attempt grade is the weighted average of its group-type grades, using the group-type weights.
- Each subject uses its latest complete attempt, so a passed retake replaces the earlier failed attempt.
- `avg_grade` is the ECTS-weighted average of those subject grades. It is null when no subject has a complete attempt.

**Status**

`404` if the student does not exist.

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

// 3. Grade rows: every group type of every attempted subject instance, with the grade if any.
//    Weights come from that instance's group types, so they are the weights of that cycle.
MATCH (st:Student {idx: $student_idx})-[:REGISTERED_IN]->(:Group)-[:OF_TYPE]->(:GroupType)<-[:HAS_TYPE]-(si:SubjectInstance)
WITH DISTINCT st, si
MATCH (si)-[:INSTANCE_OF]->(su:Subject)
MATCH (si)-[:OFFERED_IN]->(ac:AcademicCycle)
MATCH (si)-[:HAS_TYPE]->(gt:GroupType)
OPTIONAL MATCH (st)-[r:REGISTERED_IN]->(:Group)-[:OF_TYPE]->(gt)
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

**Allowed:** Teacher (own groups only). Another teacher's groups: `GET /teachers/{idx}/groups` (`user_endpoints.md`).

**Request**

None.

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
		"cycle_start": Date?,
		"cycle_end": Date?,
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
MATCH (t:Teacher {idx: $idx})-[:TEACHES]->(g:Group)-[:OF_TYPE]->(gt:GroupType)<-[:HAS_TYPE]-(si:SubjectInstance)
MATCH (si)-[:INSTANCE_OF]->(su:Subject)
MATCH (si)-[:OFFERED_IN]->(ac:AcademicCycle)
OPTIONAL MATCH (g)-[:IN_ROOM]->(r:Room)
RETURN
  g.id AS group_id,
  su.code AS course_code,
  su.name AS course_name,
  gt.g_type AS g_type,
  g.number AS group_num,
  g.weekday AS weekday,
  g.start_time AS start,
  g.end_time AS end,
  g.pnp AS pnp,
  ac.year AS cycle_year,
  ac.season AS cycle_season,
  ac.start_date AS cycle_start,
  ac.end_date AS cycle_end,
  r.building AS building,
  r.room_num AS room_num
ORDER BY ac.year DESC, ac.season, su.name, gt.g_type, g.number
```

---

## GET /groups/{group_id}/students

**Allowed:** Admin; Teacher, only for groups they teach (403 otherwise)

**Request**

No body; parameters go in the URL:

```http
GET /groups/96992b82-07dc-58c0-b3bf-4d64e58ad87f/students
```

- `group_id` (path): group id.

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

## PUT /groups/{group_id}/students/{student_idx}/grade

**Allowed:** Admin; Teacher, only for groups they teach (403 otherwise)

**Request**

```http
PUT /groups/96992b82-07dc-58c0-b3bf-4d64e58ad87f/students/279413/grade
```

```json
{
	"grade": Float
}
```

The grade belongs to the student's place in the group, so both ids go in the path. `PUT` sets the grade, replacing a previous one. `grade` must be one of `2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0`; any other value is rejected with `422`.

**Response**

```json
{
	"group_id": String,
	"student_idx": String,
	"grade": Float
}
```

**Status**

`200` with the saved grade. `404` if the student is not registered in the group.

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
