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

### (student) Show registrations

```json
{
	"student_id": Integer
}
```

```json
{
	available_registrations: List[Registrations]
	
	Registrations = {
		"id": Integer,
		"date": Date,
		"start": Time,
		"end": Time
	}
}
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
		"type": String,
		"count": Integer
	}
}
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
	"ok": Boolean
}
```
### (student) List my Academic Cycles

```json
{}
```

```json
{}
```
### (student) My Academic Cycle detail

```json
{}
```

```json
{}
```
