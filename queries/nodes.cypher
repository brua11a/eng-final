CALL apoc.load.json("file:///nodes/teachers.json") YIELD value AS trow
MERGE (t:Teacher {idx: trow.idx})
SET t.name = trow.name, t.surname = trow.surname, t.phone = trow.phone,
    t.degree = trow.degree, t.photo = trow.photo, t.working_since = date(trow.working_since)
FOREACH (_ IN CASE WHEN trow.email IS NOT NULL THEN [1] ELSE [] END |
    SET t:User, t.email = trow.email, t.passwd_hash = trow.passwd_hash);

CALL apoc.load.json("file:///nodes/students.json") YIELD value AS strow
MERGE (st:Student {idx: strow.idx})
SET st.phone = strow.phone, st.photo = strow.photo, st.joined = datetime(strow.joined)
FOREACH (_ IN CASE WHEN strow.email IS NOT NULL THEN [1] ELSE [] END |
    SET st:User, st.email = strow.email, st.passwd_hash = strow.passwd_hash);

CALL apoc.load.json("file:///nodes/curriculums.json") YIELD value AS curow
MERGE (c:Curriculum {id: curow.id})
SET c.name = curow.name;

CALL apoc.load.json("file:///nodes/faculties.json") YIELD value AS farow
MERGE (fa:Faculty {id: farow.id})
SET fa.name = farow.name, fa.full_name = farow.full_name;

CALL apoc.load.json("file:///nodes/subjects.json") YIELD value AS surow
MERGE (su:Subject {code: surow.code})
SET su.name = surow.name, su.ects = surow.ects;

CALL apoc.load.json("file:///nodes/terms.json") YIELD value AS ctrow
MERGE (fi:CurriculumTerm {id: ctrow.id})
SET fi.sem = ctrow.sem;

CALL apoc.load.json("file:///nodes/groups.json") YIELD value AS grow
MERGE (g:Group {id: grow.id})
SET g.weekday = grow.weekday,
    g.number = grow.number,
    g.type = grow.type,
    g.pnp = grow.pnp,
    g.building = grow.building,
    g.room_num = grow.room_num,
    g.start_hr = time(grow.start_hr),
    g.end_time = time(grow.end_time);