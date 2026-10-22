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
	"term_ids": List[Integer],
	"err": String?
}
```

```cypher
MATCH (st:Student {idx: $student_idx})
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

### (admin | teacher) List Students in Group

```json
{
	"group_id": Integer
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
		"joined": ZonedDateTime
	}
}
```

```cypher
MATCH (g:Group {id: $group_id})
MATCH (st:Student)-[:REGISTERED_IN]->(g)

RETURN
  st.idx AS idx,
  st.name AS name,
  st.surname AS surname,
  st.phone AS phone,
  st.photo AS photo,
  st.joined AS joined

ORDER BY st.surname, st.name
```