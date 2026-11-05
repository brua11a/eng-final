LOAD CSV WITH HEADERS FROM "file:///nodes/terms.csv" AS ctrow
MATCH (c:Curriculum {id: ctrow.curriculum_id})
MATCH (ct:CurriculumTerm {id: ctrow.id})
MERGE (c)-[:HAS_TERM]->(ct);

LOAD CSV WITH HEADERS FROM "file:///nodes/terms.csv" AS ctrow
WITH ctrow WHERE ctrow.cycle_id <> ""
MATCH (ct:CurriculumTerm {id: ctrow.id})
MATCH (ac:AcademicCycle {id: ctrow.cycle_id})
MERGE (ct)-[:TAUGHT_IN]->(ac);

LOAD CSV WITH HEADERS FROM "file:///edges/term_subjects.csv" AS csrow
MATCH (c:Curriculum {id: csrow.curriculum_id})-[:HAS_TERM]->(ct:CurriculumTerm {sem: toInteger(csrow.sem)})
MATCH (su:Subject {code: csrow.subject_code})
MERGE (ct)-[:INCLUDES]->(su);

LOAD CSV WITH HEADERS FROM "file:///nodes/subject_instances.csv" AS sirow
MATCH (si:SubjectInstance {id: sirow.id})
MATCH (su:Subject {code: sirow.subject_code})
MATCH (ac:AcademicCycle {id: sirow.cycle_id})
MERGE (si)-[:INSTANCE_OF]->(su)
MERGE (si)-[:OFFERED_IN]->(ac);

LOAD CSV WITH HEADERS FROM "file:///nodes/curriculums.csv" AS curow
MATCH (p:Programme {id: curow.programme_id})
MATCH (c:Curriculum {id: curow.id})
MERGE (p)-[:HAS_CURRICULUM]->(c);

LOAD CSV WITH HEADERS FROM "file:///edges/programme_faculties.csv" AS pfrow
MATCH (p:Programme {id: pfrow.programme_id})
MATCH (fa:Faculty {id: pfrow.faculty_id})
MERGE (p)-[:OFFERED_BY]->(fa);

LOAD CSV WITH HEADERS FROM "file:///nodes/groups.csv" AS grow
MATCH (g:Group {id: grow.id})
MATCH (r:Room {id: grow.room_id})
MERGE (g)-[:IN_ROOM]->(r);

LOAD CSV WITH HEADERS FROM "file:///nodes/group_types.csv" AS gtrow
MATCH (su:Subject {code: gtrow.subject_code})
MATCH (gt:GroupType {id: gtrow.id})
MERGE (su)-[:HAS_TYPE]->(gt);

LOAD CSV WITH HEADERS FROM "file:///nodes/groups.csv" AS grow
MATCH (g:Group {id: grow.id})
MATCH (gt:GroupType {id: grow.group_type_id})
MERGE (g)-[:OF_TYPE]->(gt);

LOAD CSV WITH HEADERS FROM "file:///edges/instance_groups.csv" AS igrow
MATCH (si:SubjectInstance {id: igrow.instance_id})
MATCH (g:Group {id: igrow.group_id})
MERGE (si)-[:HAS_GROUP]->(g);

LOAD CSV WITH HEADERS FROM "file:///edges/teacher_group.csv" AS row
MATCH (t:Teacher {idx: row.teacher_idx})
MATCH (g:Group {id: row.group_id})
MERGE (t)-[:TEACHES]->(g);

LOAD CSV WITH HEADERS FROM "file:///edges/teacher_faculty.csv" AS tfrow
MATCH (t:Teacher {idx: tfrow.teacher_idx})
MATCH (fa:Faculty {id: tfrow.faculty_id})
MERGE (t)-[:WORKS_AT]->(fa);

LOAD CSV WITH HEADERS FROM "file:///edges/student_enrolled.csv" AS serow
MATCH (st:Student {idx: serow.student_idx})
MATCH (ct:CurriculumTerm {id: serow.term_id})
MERGE (st)-[:ENROLLED]->(ct);

LOAD CSV WITH HEADERS FROM "file:///edges/student_registered.csv" AS srrow
MATCH (st:Student {idx: srrow.student_idx})
MATCH (g:Group {id: srrow.group_id})
MERGE (st)-[r:REGISTERED_IN]->(g)
SET r.registered_at = datetime(srrow.registered_at);

LOAD CSV WITH HEADERS FROM "file:///nodes/opinions.csv" AS orow
MATCH (o:Opinion {id: orow.id})
MATCH (st:Student {idx: orow.student_idx})
MATCH (g:Group {id: orow.group_id})
MERGE (st)-[:WRITES]->(o)
MERGE (o)-[:ABOUT]->(g);

LOAD CSV WITH HEADERS FROM "file:///nodes/registrations.csv" AS regrow
MATCH (reg:Registration {id: regrow.id})
MATCH (ac:AcademicCycle {id: regrow.cycle_id})
MATCH (fa:Faculty {id: regrow.faculty_id})
MERGE (reg)-[:FOR_CYCLE]->(ac)
MERGE (reg)-[:FOR_FACULTY]->(fa);

LOAD CSV WITH HEADERS FROM "file:///nodes/registration_turns.csv" AS rtrow
MATCH (reg:Registration {id: rtrow.registration_id})
MATCH (rt:RegistrationTurn {id: rtrow.id})
MERGE (reg)-[:HAS_TURN]->(rt);

LOAD CSV WITH HEADERS FROM "file:///edges/registration_groups.csv" AS rgrow
MATCH (reg:Registration {id: rgrow.registration_id})-[:FOR_CYCLE]->(ac:AcademicCycle)
MATCH (reg)-[:FOR_FACULTY]->(fa:Faculty)
MATCH (g:Group {id: rgrow.group_id})<-[:HAS_GROUP]-(si:SubjectInstance)-[:OFFERED_IN]->(ac)
MATCH (si)-[:INSTANCE_OF]->(su:Subject)
MATCH (g)-[:OF_TYPE]->(:GroupType)<-[:HAS_TYPE]-(su)
MATCH (ct:CurriculumTerm)-[:INCLUDES]->(su)
MATCH (ct)-[:TAUGHT_IN]->(ac)
MATCH (ct)<-[:HAS_TERM]-(:Curriculum)<-[:HAS_CURRICULUM]-(:Programme)-[:OFFERED_BY]->(fa)
MERGE (reg)-[:OPENS]->(g);

LOAD CSV WITH HEADERS FROM "file:///nodes/turn_assignments.csv" AS asgrow
MATCH (asg:TurnAssignment {id: asgrow.id})
MATCH (st:Student {idx: asgrow.student_idx})
MATCH (c:Curriculum {id: asgrow.curriculum_id})<-[:HAS_CURRICULUM]-(:Programme)-[:OFFERED_BY]->(fa:Faculty)
MATCH (ac:AcademicCycle {id: asgrow.cycle_id})
MATCH (rt:RegistrationTurn)<-[:HAS_TURN]-(reg:Registration)-[:FOR_CYCLE]->(ac)
MATCH (reg)-[:FOR_FACULTY]->(fa)
WHERE rt.turn_number = toInteger(asgrow.turn_number)
WITH asg, st, c, rt, reg
ORDER BY reg.id
WITH asg, st, c, head(collect(rt)) AS rt
MERGE (st)-[:ASSIGNED]->(asg)
MERGE (asg)-[:FOR_CURRICULUM]->(c)
MERGE (asg)-[:FOR_TURN]->(rt)
