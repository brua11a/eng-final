-- Loads the same CSV files as queries/nodes.cypher and queries/edges.cypher.
-- Run once by the PostgreSQL image on an empty data directory (docker-entrypoint-initdb.d),
-- inside a single transaction: either everything is imported, or nothing.
--
-- Node and edge files are first copied as text into temporary staging tables, because an N:1
-- edge (e.g. programme -> faculty) is stored in the same row as the node it starts from.

\set ON_ERROR_STOP on
BEGIN;

CREATE TEMP TABLE s_students   (idx text, name text, surname text, phone text, photo text, joined text, email text, passwd_hash text);
CREATE TEMP TABLE s_teachers   (idx text, name text, surname text, phone text, degree text, working_since text, email text, passwd_hash text);
CREATE TEMP TABLE s_admins     (idx text, name text, surname text, phone text, email text, passwd_hash text);
CREATE TEMP TABLE s_faculties  (id text, name text, full_name text);
CREATE TEMP TABLE s_programmes (id text, name text);
CREATE TEMP TABLE s_programme_faculties (programme_id text, faculty_id text);
CREATE TEMP TABLE s_curriculums (id text, intake_year text);
CREATE TEMP TABLE s_programme_curriculums (programme_id text, curriculum_id text);
CREATE TEMP TABLE s_cycles     (id text, year text, season text, start_date text, end_date text);
CREATE TEMP TABLE s_terms      (id text, sem text);
CREATE TEMP TABLE s_curriculum_terms (curriculum_id text, term_id text);
CREATE TEMP TABLE s_term_cycles (term_id text, cycle_id text);
CREATE TEMP TABLE s_rooms      (id text, building text, room_num text);
CREATE TEMP TABLE s_group_types (id text, g_type text, weight text);
CREATE TEMP TABLE s_instance_group_types (subject_code text, cycle_id text, group_type_id text);
CREATE TEMP TABLE s_groups     (id text, weekday text, number text, pnp text, capacity text, start_time text, end_time text);
CREATE TEMP TABLE s_group_of_type (group_id text, group_type_id text);
CREATE TEMP TABLE s_group_rooms (group_id text, room_id text);
CREATE TEMP TABLE s_registrations (id text, name text, reg_type text);
CREATE TEMP TABLE s_registration_for_cycle (registration_id text, cycle_id text);
CREATE TEMP TABLE s_registration_for_faculty (registration_id text, faculty_id text);
CREATE TEMP TABLE s_turns      (id text, turn_number text, date text, start_time text, end_time text);
CREATE TEMP TABLE s_registration_has_turn (registration_id text, turn_id text);
CREATE TEMP TABLE s_turn_assignments (student_idx text, turn_id text);
CREATE TEMP TABLE s_opinions   (id text, grade text, content text, submit text);
CREATE TEMP TABLE s_opinion_writes (opinion_id text, student_idx text);
CREATE TEMP TABLE s_opinion_about_group (opinion_id text, group_id text);
CREATE TEMP TABLE s_opinion_about_teacher (opinion_id text, teacher_idx text);

COPY s_students   FROM '/import/nodes/students.csv'   WITH (FORMAT csv, HEADER true);
COPY s_teachers   FROM '/import/nodes/teachers.csv'   WITH (FORMAT csv, HEADER true);
COPY s_admins     FROM '/import/nodes/admins.csv'     WITH (FORMAT csv, HEADER true);
COPY s_faculties  FROM '/import/nodes/faculties.csv'  WITH (FORMAT csv, HEADER true);
COPY s_programmes FROM '/import/nodes/programmes.csv' WITH (FORMAT csv, HEADER true);
COPY s_programme_faculties FROM '/import/edges/programme_faculties.csv' WITH (FORMAT csv, HEADER true);
COPY s_curriculums FROM '/import/nodes/curriculums.csv' WITH (FORMAT csv, HEADER true);
COPY s_programme_curriculums FROM '/import/edges/programme_curriculums.csv' WITH (FORMAT csv, HEADER true);
COPY s_cycles     FROM '/import/nodes/academic_cycles.csv' WITH (FORMAT csv, HEADER true);
COPY s_terms      FROM '/import/nodes/terms.csv'      WITH (FORMAT csv, HEADER true);
COPY s_curriculum_terms FROM '/import/edges/curriculum_terms.csv' WITH (FORMAT csv, HEADER true);
COPY s_term_cycles FROM '/import/edges/term_cycles.csv' WITH (FORMAT csv, HEADER true);
COPY s_rooms      FROM '/import/nodes/rooms.csv'      WITH (FORMAT csv, HEADER true);
COPY s_group_types FROM '/import/nodes/group_types.csv' WITH (FORMAT csv, HEADER true);
COPY s_instance_group_types FROM '/import/edges/instance_group_types.csv' WITH (FORMAT csv, HEADER true);
COPY s_groups     FROM '/import/nodes/groups.csv'     WITH (FORMAT csv, HEADER true);
COPY s_group_of_type FROM '/import/edges/group_of_type.csv' WITH (FORMAT csv, HEADER true);
COPY s_group_rooms FROM '/import/edges/group_rooms.csv' WITH (FORMAT csv, HEADER true);
COPY s_registrations FROM '/import/nodes/registrations.csv' WITH (FORMAT csv, HEADER true);
COPY s_registration_for_cycle FROM '/import/edges/registration_for_cycle.csv' WITH (FORMAT csv, HEADER true);
COPY s_registration_for_faculty FROM '/import/edges/registration_for_faculty.csv' WITH (FORMAT csv, HEADER true);
COPY s_turns      FROM '/import/nodes/registration_turns.csv' WITH (FORMAT csv, HEADER true);
COPY s_registration_has_turn FROM '/import/edges/registration_has_turn.csv' WITH (FORMAT csv, HEADER true);
COPY s_turn_assignments FROM '/import/edges/turn_assignments.csv' WITH (FORMAT csv, HEADER true);
COPY s_opinions   FROM '/import/nodes/opinions.csv'   WITH (FORMAT csv, HEADER true);
COPY s_opinion_writes FROM '/import/edges/opinion_writes.csv' WITH (FORMAT csv, HEADER true);
COPY s_opinion_about_group FROM '/import/edges/opinion_about_group.csv' WITH (FORMAT csv, HEADER true);
COPY s_opinion_about_teacher FROM '/import/edges/opinion_about_teacher.csv' WITH (FORMAT csv, HEADER true);

-- People: one `person` row, plus one row per role and an `app_user` row when there is an e-mail.
-- The same person may appear in several files (several roles): the first row wins.
INSERT INTO person (idx, name, surname, phone, photo)
SELECT idx, name, surname, phone, nullif(photo, '') FROM s_students ON CONFLICT (idx) DO NOTHING;
INSERT INTO person (idx, name, surname, phone)
SELECT idx, name, surname, phone FROM s_teachers ON CONFLICT (idx) DO NOTHING;
INSERT INTO person (idx, name, surname, phone)
SELECT idx, name, surname, phone FROM s_admins ON CONFLICT (idx) DO NOTHING;

INSERT INTO student (idx, joined) SELECT idx, joined::timestamptz FROM s_students;
INSERT INTO teacher (idx, degree, working_since) SELECT idx, degree, working_since::date FROM s_teachers;
INSERT INTO admin (idx) SELECT idx FROM s_admins;

INSERT INTO app_user (idx, email, passwd_hash)
SELECT idx, email, passwd_hash FROM (
    SELECT idx, email, passwd_hash FROM s_students
    UNION ALL SELECT idx, email, passwd_hash FROM s_teachers
    UNION ALL SELECT idx, email, passwd_hash FROM s_admins
) u
WHERE coalesce(email, '') <> ''
ON CONFLICT (idx) DO NOTHING;

-- Teaching offer
INSERT INTO faculty SELECT id, name, full_name FROM s_faculties;

INSERT INTO programme (id, name, faculty_id)
SELECT p.id, p.name, pf.faculty_id
FROM s_programmes p JOIN s_programme_faculties pf ON pf.programme_id = p.id;

INSERT INTO curriculum (id, intake_year, programme_id)
SELECT c.id, c.intake_year, pc.programme_id
FROM s_curriculums c JOIN s_programme_curriculums pc ON pc.curriculum_id = c.id;

INSERT INTO academic_cycle
SELECT id, year, season, start_date::date, end_date::date FROM s_cycles;

INSERT INTO curriculum_term (id, sem, curriculum_id, cycle_id)
SELECT t.id, t.sem::integer, ct.curriculum_id, tc.cycle_id
FROM s_terms t
JOIN s_curriculum_terms ct ON ct.term_id = t.id
LEFT JOIN s_term_cycles tc ON tc.term_id = t.id;

COPY subject (code, name, ects) FROM '/import/nodes/subjects.csv' WITH (FORMAT csv, HEADER true);
COPY term_subject (term_id, subject_code) FROM '/import/edges/term_subjects.csv' WITH (FORMAT csv, HEADER true);
COPY subject_instance (subject_code, cycle_id) FROM '/import/edges/subject_instances.csv' WITH (FORMAT csv, HEADER true);

INSERT INTO group_type (id, g_type, weight, subject_code, cycle_id)
SELECT gt.id, gt.g_type, gt.weight::double precision, igt.subject_code, igt.cycle_id
FROM s_group_types gt JOIN s_instance_group_types igt ON igt.group_type_id = gt.id;

-- Classes
INSERT INTO room SELECT id, building, room_num FROM s_rooms;

INSERT INTO class_group (id, number, capacity, weekday, start_time, end_time, pnp, group_type_id, room_id)
SELECT g.id, g.number::integer, g.capacity::integer, g.weekday::integer,
       g.start_time::time, g.end_time::time, g.pnp, got.group_type_id, gr.room_id
FROM s_groups g
JOIN s_group_of_type got ON got.group_id = g.id
LEFT JOIN s_group_rooms gr ON gr.group_id = g.id;

COPY teaches (teacher_idx, group_id) FROM '/import/edges/teacher_group.csv' WITH (FORMAT csv, HEADER true);
COPY works_at (teacher_idx, faculty_id) FROM '/import/edges/teacher_faculty.csv' WITH (FORMAT csv, HEADER true);
COPY enrolled (student_idx, term_id) FROM '/import/edges/student_enrolled.csv' WITH (FORMAT csv, HEADER true);
COPY registered_in (student_idx, group_id, registered_at) FROM '/import/edges/student_registered.csv' WITH (FORMAT csv, HEADER true);

-- Registrations
INSERT INTO registration (id, name, reg_type, cycle_id, faculty_id)
SELECT r.id, r.name, r.reg_type, rc.cycle_id, rf.faculty_id
FROM s_registrations r
JOIN s_registration_for_cycle rc ON rc.registration_id = r.id
JOIN s_registration_for_faculty rf ON rf.registration_id = r.id;

INSERT INTO registration_turn (id, turn_number, date, start_time, end_time, registration_id)
SELECT t.id, t.turn_number::integer, t.date::date, t.start_time::time, t.end_time::time, rt.registration_id
FROM s_turns t JOIN s_registration_has_turn rt ON rt.turn_id = t.id;

COPY opens (registration_id, group_id) FROM '/import/edges/registration_groups.csv' WITH (FORMAT csv, HEADER true);

INSERT INTO assigned (student_idx, turn_id, registration_id)
SELECT ta.student_idx, ta.turn_id, rt.registration_id
FROM s_turn_assignments ta JOIN registration_turn rt ON rt.id = ta.turn_id;

-- Opinions
INSERT INTO opinion (id, grade, content, submit, student_idx, group_id, teacher_idx)
SELECT o.id, o.grade::numeric, nullif(o.content, ''), o.submit::timestamptz,
       w.student_idx, ag.group_id, at.teacher_idx
FROM s_opinions o
JOIN s_opinion_writes w ON w.opinion_id = o.id
JOIN s_opinion_about_group ag ON ag.opinion_id = o.id
JOIN s_opinion_about_teacher at ON at.opinion_id = o.id;

COMMIT;

ANALYZE;
