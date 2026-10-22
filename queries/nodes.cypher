LOAD CSV WITH HEADERS FROM "file:///nodes/teachers.csv" AS trow
MERGE (t:Teacher {idx: trow.idx})
SET t.name = trow.name, t.surname = trow.surname,
    t.phone = trow.phone, t.degree = trow.degree,
    t.photo = nullif(trow.photo, ""), t.working_since = date(trow.working_since)
FOREACH (_ IN CASE WHEN trow.email <> "" THEN [1] ELSE [] END |
    SET t:User, t.email = trow.email, t.passwd_hash = trow.passwd_hash);

LOAD CSV WITH HEADERS FROM "file:///nodes/admins.csv" AS arow
MERGE (a:User:Admin {email: arow.email})
SET a.passwd_hash = arow.passwd_hash, a.kind = arow.kind;

LOAD CSV WITH HEADERS FROM "file:///nodes/students.csv" AS strow
MERGE (st:Student {idx: strow.idx})
SET st.name = strow.name, st.surname = strow.surname,
    st.phone = strow.phone, st.photo = nullif(strow.photo, ""),
    st.joined = datetime(strow.joined),
    st.avg_grade = toFloat(nullif(strow.avg_grade, ""))
FOREACH (_ IN CASE WHEN strow.email <> "" THEN [1] ELSE [] END |
    SET st:User, st.email = strow.email, st.passwd_hash = strow.passwd_hash);

LOAD CSV WITH HEADERS FROM "file:///nodes/programmes.csv" AS prow
MERGE (p:Programme {id: toInteger(prow.id)})
SET p.name = prow.name;

LOAD CSV WITH HEADERS FROM "file:///nodes/curriculums.csv" AS curow
MERGE (c:Curriculum {id: toInteger(curow.id)})
SET c.intake_year = curow.intake_year;

LOAD CSV WITH HEADERS FROM "file:///nodes/faculties.csv" AS farow
MERGE (fa:Faculty {id: toInteger(farow.id)})
SET fa.name = farow.name, fa.full_name = farow.full_name;

LOAD CSV WITH HEADERS FROM "file:///nodes/subjects.csv" AS surow
MERGE (su:Subject {code: surow.code})
SET su.name = surow.name, su.ects = toInteger(nullif(surow.ects, ""));

LOAD CSV WITH HEADERS FROM "file:///nodes/terms.csv" AS ctrow
MERGE (ct:CurriculumTerm {id: toInteger(ctrow.id)})
SET ct.sem = toInteger(ctrow.sem);

LOAD CSV WITH HEADERS FROM "file:///nodes/academic_cycles.csv" AS acrow
MERGE (ac:AcademicCycle {id: toInteger(acrow.id)})
SET ac.year = acrow.year, ac.season = acrow.season;

LOAD CSV WITH HEADERS FROM "file:///nodes/rooms.csv" AS rrow
MERGE (r:Room {id: toInteger(rrow.id)})
SET r.building = rrow.building, r.room_num = rrow.room_num;

LOAD CSV WITH HEADERS FROM "file:///nodes/groups.csv" AS grow
MERGE (g:Group {id: toInteger(grow.id)})
SET g.weekday = toInteger(grow.weekday),
    g.number = toInteger(grow.number),
    g.g_type = grow.g_type,
    g.pnp = grow.pnp,
    g.capacity = toInteger(grow.capacity),
    g.start_hr = time(grow.start_hr),
    g.end_time = time(grow.end_time);

LOAD CSV WITH HEADERS FROM "file:///nodes/registrations.csv" AS regrow
MERGE (reg:Registration {id: toInteger(regrow.id)})
SET reg.name = regrow.name,
    reg.reg_type = regrow.reg_type;

LOAD CSV WITH HEADERS FROM "file:///nodes/registration_turns.csv" AS rtrow
MERGE (rt:RegistrationTurn {id: toInteger(rtrow.id)})
SET rt.turn_number = toInteger(rtrow.turn_number),
    rt.date = date(rtrow.date),
    rt.start_hr = time(rtrow.start_hr),
    rt.end_time = time(rtrow.end_time);

LOAD CSV WITH HEADERS FROM "file:///nodes/turn_assignments.csv" AS asgrow
MERGE (asg:TurnAssignment {id: toInteger(asgrow.id)});

LOAD CSV WITH HEADERS FROM "file:///nodes/opinions.csv" AS orow
MERGE (o:Opinion {id: toInteger(orow.id)})
SET o.grade = toFloat(orow.grade),
    o.content = nullif(orow.content, ""),
    o.submit = datetime(orow.submit);
