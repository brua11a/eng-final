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
		"phone": String?,
		"degree": String,
		"photo": String?,
		"working_since": Date,
		"faculty": String
	}
}
```
### (user) Find Teacher

```json
{
	"name": String
}
```

```json
	teachers: List[Teacher]
	
	Teacher = {
		"idx": String,
		"name": String,
		"surname": String,
		"phone": String?,
		"degree": String,
		"photo": String?,
		"working_since": Date,
		"faculty": String
	}
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
		"ects": Integer,
		"groups": List[Group]
	}
	
	Group = {
		"id": Integer,
		"weekday": Integer,
		"type": String,
		"number": Integer,
		"pnp": String,
		"capacity": Integer,
		"start_hr": ZonedTime,
		"end_time": ZonedTime,
		"subject_code": String,
		"cycle_id": Integer,
		"room_id": Integer,
	}
}
```
### (user) Find Subject

```json
{
	"name": String
}
```

```json
{
	subject_and_groups: List[SubjectAndGroup]
	
	SubjectAndGroup = {
		"code": String,
		"name": String,
		"ects": Integer,
		"groups": List[Group]
	}
	
	Group = {
		"id": Integer,
		"weekday": Integer,
		"type": String,
		"number": Integer,
		"pnp": String,
		"capacity": Integer,
		"start_hr": ZonedTime,
		"end_time": ZonedTime,
		"subject_code": String,
		"cycle_id": Integer,
		"room_id": Integer,
	}
}
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
		"name": String,
		"faculty_id": Integer
	}
}
```
### (user) Find Curriculum

```json
{
	"name": String
}
```

```json
{
	curricula: List[Curriculum]
	
	Curriculum = {
		"id": Integer,
		"name": String,
		"faculty_id": Integer
	}
}
```
### (user) Subject detail

```json
{
	"course_ud": Integer
}
```

```json
{}
```
### (user) List Subject groups

```json
{}
```

```json
{}
```
### (user) Group detail

```json
{}
```

```json
{}
```
### (user) Teacher detail

```json
{}
```

```json
{}
```
### (user) Me

```json
{}
```

```json
{}
```