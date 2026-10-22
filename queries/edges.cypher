LOAD CSV WITH HEADERS FROM "file:///nodes/terms.csv" AS ctrow
MATCH (c:Curriculum {id: toInteger(ctrow.curriculum_id)})
MATCH (ct:CurriculumTerm {id: toInteger(ctrow.id)})
MERGE (c)-[:HAS_TERM]->(ct);

LOAD CSV WITH HEADERS FROM "file:///nodes/terms.csv" AS ctrow
WITH ctrow WHERE ctrow.cycle_id <> ""
MATCH (ct:CurriculumTerm {id: toInteger(ctrow.id)})
MATCH (ac:AcademicCycle {id: toInteger(ctrow.cycle_id)})
MERGE (ct)-[:TAUGHT_IN]->(ac);

LOAD CSV WITH HEADERS FROM "file:///edges/term_subjects.csv" AS csrow
MATCH (c:Curriculum {id: toInteger(csrow.curriculum_id)})-[:HAS_TERM]->(ct:CurriculumTerm {sem: toInteger(csrow.sem)})
MATCH (su:Subject {code: csrow.subject_code})
MERGE (ct)-[:INCLUDES]->(su);

LOAD CSV WITH HEADERS FROM "file:///nodes/curriculums.csv" AS curow
MATCH (p:Programme {id: toInteger(curow.programme_id)})
MATCH (c:Curriculum {id: toInteger(curow.id)})
MERGE (p)-[:HAS_CURRICULUM]->(c);

LOAD CSV WITH HEADERS FROM "file:///edges/programme_faculties.csv" AS pfrow
MATCH (p:Programme {id: toInteger(pfrow.programme_id)})
MATCH (fa:Faculty {id: toInteger(pfrow.faculty_id)})
MERGE (p)-[:OFFERED_BY]->(fa);

LOAD CSV WITH HEADERS FROM "file:///nodes/groups.csv" AS grow
MATCH (g:Group {id: toInteger(grow.id)})
MATCH (r:Room {id: toInteger(grow.room_id)})
MERGE (g)-[:IN_ROOM]->(r);

LOAD CSV WITH HEADERS FROM "file:///edges/group_subject.csv" AS gsrow
MATCH (g:Group {id: toInteger(gsrow.group_id)})
MATCH (su:Subject {code: gsrow.subject_code})
MERGE (g)-[:OF_SUBJECT]->(su);

LOAD CSV WITH HEADERS FROM "file:///edges/teacher_group.csv" AS row
MATCH (t:Teacher {idx: row.teacher_idx})
MATCH (g:Group {id: toInteger(row.group_id)})
MERGE (t)-[:TEACHES]->(g);

LOAD CSV WITH HEADERS FROM "file:///edges/teacher_faculty.csv" AS tfrow
MATCH (t:Teacher {idx: tfrow.teacher_idx})
MATCH (fa:Faculty {id: toInteger(tfrow.faculty_id)})
MERGE (t)-[:WORKS_AT]->(fa);

LOAD CSV WITH HEADERS FROM "file:///edges/student_enrolled.csv" AS serow
MATCH (st:Student {idx: serow.student_idx})
MATCH (ct:CurriculumTerm {id: toInteger(serow.term_id)})
MERGE (st)-[:ENROLLED]->(ct);

LOAD CSV WITH HEADERS FROM "file:///edges/student_registered.csv" AS srrow
MATCH (st:Student {idx: srrow.student_idx})
MATCH (g:Group {id: toInteger(srrow.group_id)})
MERGE (st)-[r:REGISTERED_IN]->(g)
SET r.registered_at = datetime(srrow.registered_at);

LOAD CSV WITH HEADERS FROM "file:///nodes/opinions.csv" AS orow
MATCH (o:Opinion {id: toInteger(orow.id)})
MATCH (st:Student {idx: orow.student_idx})
MATCH (g:Group {id: toInteger(orow.group_id)})
MERGE (st)-[:WRITES]->(o)
MERGE (o)-[:ABOUT]->(g);

LOAD CSV WITH HEADERS FROM "file:///nodes/registrations.csv" AS regrow
MATCH (reg:Registration {id: toInteger(regrow.id)})
MATCH (ac:AcademicCycle {id: toInteger(regrow.cycle_id)})
MATCH (fa:Faculty {id: toInteger(regrow.faculty_id)})
MERGE (reg)-[:FOR_CYCLE]->(ac)
MERGE (reg)-[:FOR_FACULTY]->(fa);

LOAD CSV WITH HEADERS FROM "file:///nodes/registration_turns.csv" AS rtrow
MATCH (reg:Registration {id: toInteger(rtrow.registration_id)})
MATCH (rt:RegistrationTurn {id: toInteger(rtrow.id)})
MERGE (reg)-[:HAS_TURN]->(rt);

LOAD CSV WITH HEADERS FROM "file:///edges/registration_groups.csv" AS rgrow
MATCH (reg:Registration {id: toInteger(rgrow.registration_id)})-[:FOR_CYCLE]->(ac:AcademicCycle)
MATCH (reg)-[:FOR_FACULTY]->(fa:Faculty)
MATCH (g:Group {id: toInteger(rgrow.group_id)})-[:OF_SUBJECT]->(su:Subject)
MATCH (ct:CurriculumTerm)-[:INCLUDES]->(su)
MATCH (ct)-[:TAUGHT_IN]->(ac)
MATCH (ct)<-[:HAS_TERM]-(:Curriculum)<-[:HAS_CURRICULUM]-(:Programme)-[:OFFERED_BY]->(fa)
MERGE (reg)-[:OPENS]->(g);

LOAD CSV WITH HEADERS FROM "file:///nodes/turn_assignments.csv" AS asgrow
MATCH (asg:TurnAssignment {id: toInteger(asgrow.id)})
MATCH (st:Student {idx: asgrow.student_idx})
MATCH (c:Curriculum {id: toInteger(asgrow.curriculum_id)})<-[:HAS_CURRICULUM]-(:Programme)-[:OFFERED_BY]->(fa:Faculty)
MATCH (ac:AcademicCycle {id: toInteger(asgrow.cycle_id)})
MATCH (rt:RegistrationTurn)<-[:HAS_TURN]-(reg:Registration)-[:FOR_CYCLE]->(ac)
MATCH (reg)-[:FOR_FACULTY]->(fa)
WHERE rt.turn_number = toInteger(asgrow.turn_number)
WITH asg, st, c, rt, reg
ORDER BY reg.id
WITH asg, st, c, head(collect(rt)) AS rt
MERGE (st)-[:ASSIGNED]->(asg)
MERGE (asg)-[:FOR_CURRICULUM]->(c)
MERGE (asg)-[:FOR_TURN]->(rt)
