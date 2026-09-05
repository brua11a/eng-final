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
	"phone": String?,
	"photo": String?,
	"joined": ZonedDateTime,
	"err": String?
}
```

### (admin | teacher) List Students in Group

```json
{
	"group_idx": Integer
}
```

```json 
{
	students: List[Student]
	
	Student = {
		"idx": String,
		"name": String,
		"surname": String,
		"phone": String?,
		"photo": String?,
		"joined": ZonedDateTime
	}
}
```