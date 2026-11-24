-- Loads the relational data set: one CSV file per table in sql/data/.
-- Run once by the PostgreSQL image on an empty data directory (docker-entrypoint-initdb.d),
-- inside a single transaction: either everything is imported, or nothing.
--
-- The files were converted once from the graph data set (import/nodes, import/edges) and are
-- not kept in sync with it afterwards. In the conversion, every N:1 edge became a foreign key
-- column of the row it starts from (e.g. programme.faculty_id), every N:M edge a junction
-- table (e.g. teaches), and the Student/Teacher/Admin/User labels of one node a `person` row
-- with one row per role. Optional properties and optional N:1 edges have tables of
-- their own (no NULLs, see 01_schema.sql).
--
-- HEADER MATCH checks that the column names in each file are those of the table, in order.
-- Tables are loaded parents first, so each foreign key is checked against loaded rows.

\set ON_ERROR_STOP on
BEGIN;

-- People
COPY person            FROM '/data/person.csv'               WITH (FORMAT csv, HEADER match);
COPY person_photo      FROM '/data/person_photo.csv'         WITH (FORMAT csv, HEADER match);
COPY student           FROM '/data/student.csv'              WITH (FORMAT csv, HEADER match);
COPY teacher           FROM '/data/teacher.csv'              WITH (FORMAT csv, HEADER match);
COPY admin             FROM '/data/admin.csv'                WITH (FORMAT csv, HEADER match);
COPY app_user          FROM '/data/app_user.csv'             WITH (FORMAT csv, HEADER match);
COPY inactive          FROM '/data/inactive.csv'             WITH (FORMAT csv, HEADER match);

-- Teaching offer
COPY faculty           FROM '/data/faculty.csv'              WITH (FORMAT csv, HEADER match);
COPY programme         FROM '/data/programme.csv'            WITH (FORMAT csv, HEADER match);
COPY curriculum        FROM '/data/curriculum.csv'           WITH (FORMAT csv, HEADER match);
COPY academic_cycle    FROM '/data/academic_cycle.csv'       WITH (FORMAT csv, HEADER match);
COPY curriculum_term   FROM '/data/curriculum_term.csv'      WITH (FORMAT csv, HEADER match);
COPY taught_in         FROM '/data/taught_in.csv'            WITH (FORMAT csv, HEADER match);
COPY subject           FROM '/data/subject.csv'              WITH (FORMAT csv, HEADER match);
COPY subject_ects      FROM '/data/subject_ects.csv'         WITH (FORMAT csv, HEADER match);
COPY term_subject      FROM '/data/term_subject.csv'         WITH (FORMAT csv, HEADER match);
COPY subject_instance  FROM '/data/subject_instance.csv'     WITH (FORMAT csv, HEADER match);
COPY group_type        FROM '/data/group_type.csv'           WITH (FORMAT csv, HEADER match);

-- Classes
COPY room              FROM '/data/room.csv'                 WITH (FORMAT csv, HEADER match);
COPY class_group       FROM '/data/class_group.csv'          WITH (FORMAT csv, HEADER match);
COPY in_room           FROM '/data/in_room.csv'              WITH (FORMAT csv, HEADER match);
COPY teaches           FROM '/data/teaches.csv'              WITH (FORMAT csv, HEADER match);
COPY works_at          FROM '/data/works_at.csv'             WITH (FORMAT csv, HEADER match);
COPY enrolled          FROM '/data/enrolled.csv'             WITH (FORMAT csv, HEADER match);
COPY registered_in     FROM '/data/registered_in.csv'        WITH (FORMAT csv, HEADER match);
COPY grade             FROM '/data/grade.csv'                WITH (FORMAT csv, HEADER match);

-- Registrations
COPY registration      FROM '/data/registration.csv'         WITH (FORMAT csv, HEADER match);
COPY registration_turn FROM '/data/registration_turn.csv'    WITH (FORMAT csv, HEADER match);
COPY opens             FROM '/data/opens.csv'                WITH (FORMAT csv, HEADER match);
COPY assigned          FROM '/data/assigned.csv'             WITH (FORMAT csv, HEADER match);

-- Opinions
COPY opinion           FROM '/data/opinion.csv'              WITH (FORMAT csv, HEADER match);
COPY opinion_content   FROM '/data/opinion_content.csv'      WITH (FORMAT csv, HEADER match);

COMMIT;

ANALYZE;
