### (admin) Create Teacher

```json
{
	"name": String,
	"surname": String,
	"phone": String?,
	"degree": String,
	"photo": String?,
	"working_since": Date,
	"faculty_id": Integer
}
```

```json
{
	"idx": String,
	"name": String,
	"surname": String,
	"phone": String?,
	"degree": String,
	"photo": String?,
	"working_since": Date,
	"faculty_id": Integer,
	"err": String?
}
```

### (admin) Create Student

```json
{
	"name": String,
	"surname": String,
	"phone": String?,
	"photo": String?,
	"joined": ZonedDateTime
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

### (admin) Assign User to account

```json
{
	"email": String,
	"passwd": String,
	"user_type": "Teacher" | "Student",
	"assigned_id": String
}
```

```json
{
	"email": String,
	"owner_type": "Teacher" | "Student",
	"owner_idx": String,
	"err": String?
}
```

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

### (admin) Create Group

```json
{
	"weekday": Integer,
	"type": String,
	"number": Integer,
	"pnp": String,
	"capacity": Integer,
	"start_hr": ZonedTime,
	"end_time": ZonedTime,
	"subject_code": String,
	"cycle_id": Integer,
	"room_id": Integer
}
```

```json
{
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
	"err": String?
}
```
### (admin) Create room

```json
{
	"building": String,
	"room_num": String
}
```

```json
{
	"id": Integer,
	"building": String,
	"room_num": String,
	"err": String?
}
```

### (admin) Create AcademicCycle

```json
{
	"year": String,
	"season": String
}
```

```json
{
	"id": Integer,
	"year": String,
	"season": String,
	"err": String?
}
```

### (admin) Create Subject

```json
{
	"code": String,
	"name": String,
	"ects": Integer?
}
```

```json
{
	"code": String,
	"name": String,
	"ects": Integer?,
	"err": String?
}
```

### (admin) Create CurriculumTerm

```json
{
	"sem": Integer,
	"curriculum_id": Integer
}
```

```json
{
	"id": Integer,
	"sem": Integer,
	"curriculum_id": Integer,
	"err": String?
}
```

### (admin) Create Curriculum

```json
{
	"name": String,
	"faculty_id": Integer
}
```

```json
{
	"id": Integer,
	"name": String,
	"faculty_id": Integer,
	"err": String?
}
```

### (admin) Create Faculty

```json
{
	"name": String,
	"full_name": String
}
```

```json
{
	"id": Integer,
	"name": String,
	"full_name": String,
	"err": String?
}
```

### (admin | teacher) Student detail

```json
{
	"idx": String
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