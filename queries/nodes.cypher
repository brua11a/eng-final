LOAD CSV WITH HEADERS FROM "file:///nodes/teachers.csv" AS row
MERGE (t:Teacher:Person {idx: row.idx})
SET t.name = row.name, t.surname = row.surname,
    t.phone = row.phone, t.degree = row.degree,
    t.photo = nullif(row.photo, ""), t.working_since = date(row.working_since)
FOREACH (_ IN CASE WHEN row.email <> "" THEN [1] ELSE [] END |
    SET t:User, t.email = row.email, t.passwd_hash = row.passwd_hash);

LOAD CSV WITH HEADERS FROM "file:///nodes/admins.csv" AS row
MERGE (a:User:Person:Admin {idx: row.idx})
SET a.name = row.name, a.surname = row.surname, a.phone = row.phone,
    a.email = row.email, a.passwd_hash = row.passwd_hash;

LOAD CSV WITH HEADERS FROM "file:///nodes/students.csv" AS row
MERGE (st:Student:Person {idx: row.idx})
SET st.name = row.name, st.surname = row.surname,
    st.phone = row.phone, st.photo = nullif(row.photo, ""),
    st.joined = datetime(row.joined)
FOREACH (_ IN CASE WHEN row.email <> "" THEN [1] ELSE [] END |
    SET st:User, st.email = row.email, st.passwd_hash = row.passwd_hash);

LOAD CSV WITH HEADERS FROM "file:///nodes/programmes.csv" AS row
MERGE (p:Programme {id: row.id})
SET p.name = row.name;

LOAD CSV WITH HEADERS FROM "file:///nodes/curriculums.csv" AS row
MERGE (c:Curriculum {id: row.id})
SET c.intake_year = row.intake_year;

LOAD CSV WITH HEADERS FROM "file:///nodes/faculties.csv" AS row
MERGE (fa:Faculty {id: row.id})
SET fa.name = row.name, fa.full_name = row.full_name;

LOAD CSV WITH HEADERS FROM "file:///nodes/subjects.csv" AS row
MERGE (su:Subject {code: row.code})
SET su.name = row.name, su.ects = toInteger(nullif(row.ects, ""));

LOAD CSV WITH HEADERS FROM "file:///nodes/subject_instances.csv" AS row
MERGE (si:SubjectInstance {id: row.id});

LOAD CSV WITH HEADERS FROM "file:///nodes/terms.csv" AS row
MERGE (ct:CurriculumTerm {id: row.id})
SET ct.sem = toInteger(row.sem);

LOAD CSV WITH HEADERS FROM "file:///nodes/academic_cycles.csv" AS row
MERGE (ac:AcademicCycle {id: row.id})
SET ac.year = row.year, ac.season = row.season;

LOAD CSV WITH HEADERS FROM "file:///nodes/rooms.csv" AS row
MERGE (r:Room {id: row.id})
SET r.building = row.building, r.room_num = row.room_num;

LOAD CSV WITH HEADERS FROM "file:///nodes/group_types.csv" AS row
MERGE (gt:GroupType {id: row.id})
SET gt.g_type = row.g_type, gt.weight = toFloat(row.weight);

LOAD CSV WITH HEADERS FROM "file:///nodes/groups.csv" AS row
MERGE (g:Group {id: row.id})
SET g.weekday = toInteger(row.weekday),
    g.number = toInteger(row.number),
    g.pnp = row.pnp,
    g.capacity = toInteger(row.capacity),
    g.start_hr = time(row.start_hr),
    g.end_time = time(row.end_time);

LOAD CSV WITH HEADERS FROM "file:///nodes/registrations.csv" AS row
MERGE (reg:Registration {id: row.id})
SET reg.name = row.name,
    reg.reg_type = row.reg_type;

LOAD CSV WITH HEADERS FROM "file:///nodes/registration_turns.csv" AS row
MERGE (rt:RegistrationTurn {id: row.id})
SET rt.turn_number = toInteger(row.turn_number),
    rt.date = date(row.date),
    rt.start_hr = time(row.start_hr),
    rt.end_time = time(row.end_time);

LOAD CSV WITH HEADERS FROM "file:///nodes/opinions.csv" AS row
MERGE (o:Opinion {id: row.id})
SET o.grade = toFloat(row.grade),
    o.content = nullif(row.content, ""),
    o.submit = datetime(row.submit);