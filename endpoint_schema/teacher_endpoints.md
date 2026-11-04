### (admin | teacher) Student detail

```json
{
	"student_idx": String
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
	"term_ids": List[String],
	"err": String?
}
```

```cypher
MATCH (st:Student {idx: $student_idx})
OPTIONAL MATCH (st)-[:ENROLLED]->(ct:CurriculumTerm)
OPTIONAL CALL (st) {
  MATCH (st)-[:REGISTERED_IN]->(:Group)-[:OF_TYPE]->(:GroupType)<-[:HAS_TYPE]-(su:Subject)
  WITH DISTINCT st, su
  MATCH (su)-[:HAS_TYPE]->(gt:GroupType)
  OPTIONAL MATCH (st)-[rg:REGISTERED_IN]->(:Group)-[:OF_TYPE]->(gt)
  WHERE rg.grade IS NOT NULL
  WITH su, gt, avg(rg.grade) AS type_grade
  WITH su, collect({weight: gt.weight, grade: type_grade}) AS parts
  WHERE size(parts) > 0 AND all(part IN parts WHERE part.grade IS NOT NULL)
  WITH su.ects AS ects,
    reduce(total = 0.0, part IN parts | total + part.grade * part.weight)
      / reduce(total = 0.0, part IN parts | total + part.weight) AS subject_grade
  WITH sum(subject_grade * ects) AS weighted, sum(ects) AS ects_total
  RETURN CASE WHEN ects_total = 0 THEN null ELSE weighted / ects_total END AS avg_grade
}

RETURN
  st.idx AS idx,
  st.name AS name,
  st.surname AS surname,
  st.phone AS phone,
  st.photo AS photo,
  st.joined AS joined,
  avg_grade,
  collect(DISTINCT ct.id) AS term_ids
```

`REGISTERED_IN.grade` is the mark for that group. `avg_grade` is the ECTS-weighted mean of completed subject grades. A subject grade weights each group-type mark by `GroupType.weight`.

### (admin | teacher) List Students in Group

```json
{
	"group_id": String
}
```

```json 
{
	students: List[Student]
	
	Student = {
		"idx": String,
		"name": String,
		"surname": String,
		"phone": String,
		"photo": String?,
		"joined": ZonedDateTime,
		"grade": Float?
	}
}
```

```cypher
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

### (admin | teacher) Set group grade

```json
{
	"group_id": String,
	"student_idx": String,
	"grade": Float
}
```

```json
{
	"group_id": String,
	"student_idx": String,
	"grade": Float,
	"err": String?
}
```

```cypher
MATCH (st:Student {idx: $student_idx})-[r:REGISTERED_IN]->(g:Group {id: $group_id})
SET r.grade = $grade
RETURN g.id AS group_id, st.idx AS student_idx, r.grade AS grade
```

Teacher callers must teach the group; admin may grade any group. This writes `REGISTERED_IN.grade` for that student in that group. The subject grade multiplies it by the weight of the group's `GroupType`.
