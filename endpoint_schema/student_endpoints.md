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
		"date": Date,  %%this curriculum's turn inside the faculty registration%%
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
		"g_type": String,
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
	"ok": Boolean,
	"err": String?
}
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
