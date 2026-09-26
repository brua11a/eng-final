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
		"g_type": String,
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
	"name": String?,
	"id": Integer?
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
		"g_type": String,
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
	"name": String,
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
	"course_id": String
}
```

```json
{
	"name": String,
	"ects": Integer,
	"coordinated": TeacherName,
	"taught_by": List[TeacherName]
	
	TeacherName = {
		"id": String,
		"name": String
	}
}
```
### (user) List Subject groups

```json
{
	"course_id": Integer
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
		"filled": Integer,
		"capacity": Integer,
		"start_hr": ZonedTime,
		"end_time": ZonedTime,
		"subject_code": String,
		"cycle_id": Integer,
		"room_id": Integer,
	}
}
```
### (user) Group detail

```json
{
	"course_id": Integer,
	"group_num": Integer
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
### (user) Teacher detail

```json
{
	"id": String
}
```

```json
{
	"degree": String,
	"name": String,
	"phone": String?,
	"e-mail": String?,
	"groups": List[GroupAndCourse]
	
	GroupAndCourse = {
		"course_id": String,
		"g_type": String,
		"group_num": Integer
	}
}
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