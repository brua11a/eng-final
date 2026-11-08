LOAD CSV WITH HEADERS FROM "file:///edges/curriculum_terms.csv" AS row
MATCH (c:Curriculum {id: row.curriculum_id})
MATCH (ct:CurriculumTerm {id: row.term_id})
MERGE (c)-[:HAS_TERM]->(ct);

LOAD CSV WITH HEADERS FROM "file:///edges/term_cycles.csv" AS row
MATCH (ct:CurriculumTerm {id: row.term_id})
MATCH (ac:AcademicCycle {id: row.cycle_id})
MERGE (ct)-[:TAUGHT_IN]->(ac);

LOAD CSV WITH HEADERS FROM "file:///edges/term_subjects.csv" AS row
MATCH (ct:CurriculumTerm {id: row.term_id})
MATCH (su:Subject {code: row.subject_code})
MERGE (ct)-[:INCLUDES]->(su);

LOAD CSV WITH HEADERS FROM "file:///edges/programme_curriculums.csv" AS row
MATCH (p:Programme {id: row.programme_id})
MATCH (c:Curriculum {id: row.curriculum_id})
MERGE (p)-[:HAS_CURRICULUM]->(c);

LOAD CSV WITH HEADERS FROM "file:///edges/programme_faculties.csv" AS row
MATCH (p:Programme {id: row.programme_id})
MATCH (fa:Faculty {id: row.faculty_id})
MERGE (p)-[:OFFERED_BY]->(fa);

LOAD CSV WITH HEADERS FROM "file:///edges/group_rooms.csv" AS row
MATCH (g:Group {id: row.group_id})
MATCH (r:Room {id: row.room_id})
MERGE (g)-[:IN_ROOM]->(r);

LOAD CSV WITH HEADERS FROM "file:///edges/subject_instance_of.csv" AS row
MATCH (si:SubjectInstance {id: row.instance_id})
MATCH (su:Subject {code: row.subject_code})
MERGE (si)-[:INSTANCE_OF]->(su);

LOAD CSV WITH HEADERS FROM "file:///edges/subject_instance_offered_in.csv" AS row
MATCH (si:SubjectInstance {id: row.instance_id})
MATCH (ac:AcademicCycle {id: row.cycle_id})
MERGE (si)-[:OFFERED_IN]->(ac);

LOAD CSV WITH HEADERS FROM "file:///edges/instance_group_types.csv" AS row
MATCH (si:SubjectInstance {id: row.instance_id})
MATCH (gt:GroupType {id: row.group_type_id})
MERGE (si)-[:HAS_TYPE]->(gt);

LOAD CSV WITH HEADERS FROM "file:///edges/group_of_type.csv" AS row
MATCH (g:Group {id: row.group_id})
MATCH (gt:GroupType {id: row.group_type_id})
MERGE (g)-[:OF_TYPE]->(gt);

LOAD CSV WITH HEADERS FROM "file:///edges/teacher_group.csv" AS row
MATCH (t:Teacher {idx: row.teacher_idx})
MATCH (g:Group {id: row.group_id})
MERGE (t)-[:TEACHES]->(g);

LOAD CSV WITH HEADERS FROM "file:///edges/teacher_faculty.csv" AS row
MATCH (t:Teacher {idx: row.teacher_idx})
MATCH (fa:Faculty {id: row.faculty_id})
MERGE (t)-[:WORKS_AT]->(fa);

LOAD CSV WITH HEADERS FROM "file:///edges/student_enrolled.csv" AS row
MATCH (st:Student {idx: row.student_idx})
MATCH (ct:CurriculumTerm {id: row.term_id})
MERGE (st)-[:ENROLLED]->(ct);

LOAD CSV WITH HEADERS FROM "file:///edges/student_registered.csv" AS row
MATCH (st:Student {idx: row.student_idx})
MATCH (g:Group {id: row.group_id})
MERGE (st)-[r:REGISTERED_IN]->(g)
SET r.registered_at = datetime(row.registered_at);

LOAD CSV WITH HEADERS FROM "file:///edges/opinion_writes.csv" AS row
MATCH (o:Opinion {id: row.opinion_id})
MATCH (st:Student {idx: row.student_idx})
MERGE (st)-[:WRITES]->(o);

LOAD CSV WITH HEADERS FROM "file:///edges/opinion_about_group.csv" AS row
MATCH (o:Opinion {id: row.opinion_id})
MATCH (g:Group {id: row.group_id})
MERGE (o)-[:ABOUT]->(g);

LOAD CSV WITH HEADERS FROM "file:///edges/opinion_about_teacher.csv" AS row
MATCH (o:Opinion {id: row.opinion_id})
MATCH (t:Teacher {idx: row.teacher_idx})
MERGE (o)-[:ABOUT_TEACHER]->(t);

LOAD CSV WITH HEADERS FROM "file:///edges/registration_for_cycle.csv" AS row
MATCH (reg:Registration {id: row.registration_id})
MATCH (ac:AcademicCycle {id: row.cycle_id})
MERGE (reg)-[:FOR_CYCLE]->(ac);

LOAD CSV WITH HEADERS FROM "file:///edges/registration_for_faculty.csv" AS row
MATCH (reg:Registration {id: row.registration_id})
MATCH (fa:Faculty {id: row.faculty_id})
MERGE (reg)-[:FOR_FACULTY]->(fa);

LOAD CSV WITH HEADERS FROM "file:///edges/registration_has_turn.csv" AS row
MATCH (reg:Registration {id: row.registration_id})
MATCH (rt:RegistrationTurn {id: row.turn_id})
MERGE (reg)-[:HAS_TURN]->(rt);

LOAD CSV WITH HEADERS FROM "file:///edges/registration_groups.csv" AS row
MATCH (reg:Registration {id: row.registration_id})
MATCH (g:Group {id: row.group_id})
MERGE (reg)-[:OPENS]->(g);

LOAD CSV WITH HEADERS FROM "file:///edges/turn_assignments.csv" AS row
MATCH (st:Student {idx: row.student_idx})
MATCH (rt:RegistrationTurn {id: row.turn_id})
MERGE (st)-[:ASSIGNED]->(rt);
