CALL apoc.load.json("file:///nodes/terms.json") YIELD value AS ctrow
MATCH (c:Curriculum {id: ctrow.curriculum_id})
MATCH (fi:CurriculumTerm {id: ctrow.id})
MERGE (c)-[:HAS_TERM]->(fi);

CALL apoc.load.json("file:///edges/term_subjects.json") YIELD value AS csrow
MATCH (c:Curriculum {name: csrow.curriculum})-[:HAS_TERM]->(fi:CurriculumTerm {sem: csrow.sem})
MATCH (su:Subject {code: csrow.subject_code})
MERGE (fi)-[:CONTAINS]->(su);

CALL apoc.load.json("file:///edges/curriculum_faculties.json") YIELD value AS ccrow
MATCH (c:Curriculum {name: ccrow.curriculum})
MATCH (fa:Faculty {name: ccrow.faculty})
MERGE (c)-[:IS_IN]->(fa);

CALL apoc.load.json("file:///edges/group_subject.json") YIELD value AS gsrow
MATCH (g:Group {id: gsrow.group_id})
MATCH (su:Subject {code: gsrow.subject_code})
MERGE (g)-[:OF_SUBJECT]->(su);

CALL apoc.load.json("file:///edges/teacher_group.json") YIELD value AS row
MATCH (t:Teacher {idx: row.teacher_idx})
MATCH (g:Group {id: row.group_id})
MERGE (t)-[:TEACHES]->(g);