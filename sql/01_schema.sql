-- Relational counterpart of the graph model (queries/schema.cypher).
-- Each node label becomes a table; N:1 edges become foreign-key columns,
-- N:M edges become join tables. Cardinality follows the edge table in the thesis (4.3.6).
--
-- No column accepts NULL. An optional property or an optional N:1 edge is a separate table
-- whose primary key is also the foreign key to the row it belongs to (1:0..1). A missing value
-- is a missing row. ON DELETE CASCADE: such a row is part of its owner, like a property is part
-- of a node or an edge in the graph, and disappears with it.

-- People ---------------------------------------------------------------------
-- No multi-labelling in SQL: shared data lives in `person`, every role is its own table
-- whose primary key is also a foreign key to `person` (one row per role the person has).
CREATE TABLE person (
    idx      text PRIMARY KEY,
    name     text NOT NULL,
    surname  text NOT NULL,
    phone    text NOT NULL,
    UNIQUE (name, surname, phone)
);

CREATE TABLE person_photo (                                      -- optional Person.photo
    idx   text PRIMARY KEY REFERENCES person (idx) ON DELETE CASCADE,
    photo text NOT NULL
);

CREATE TABLE student (
    idx    text PRIMARY KEY REFERENCES person (idx),
    joined timestamptz NOT NULL
);

CREATE TABLE teacher (
    idx           text PRIMARY KEY REFERENCES person (idx),
    degree        text NOT NULL,
    working_since date NOT NULL
);

CREATE TABLE admin (
    idx text PRIMARY KEY REFERENCES person (idx)
);

-- Login data (label User).
CREATE TABLE app_user (
    idx         text PRIMARY KEY REFERENCES person (idx),
    email       text NOT NULL UNIQUE,
    passwd_hash text NOT NULL
);

-- Label Inactive. It references app_user, not person: only an account can be deactivated,
-- which the graph type cannot express (Inactive => User is not allowed, 5.3.1).
CREATE TABLE inactive (
    idx            text PRIMARY KEY REFERENCES app_user (idx) ON DELETE CASCADE,
    deactivated_at timestamptz NOT NULL
);

-- Teaching offer --------------------------------------------------------------
CREATE TABLE faculty (
    id        text PRIMARY KEY,
    name      text NOT NULL,
    full_name text NOT NULL
);

CREATE TABLE programme (
    id         text PRIMARY KEY,
    name       text NOT NULL UNIQUE,
    faculty_id text NOT NULL REFERENCES faculty (id)            -- OFFERED_BY (N:1)
);

CREATE TABLE curriculum (
    id           text PRIMARY KEY,
    intake_year  text NOT NULL,
    programme_id text NOT NULL REFERENCES programme (id)        -- HAS_CURRICULUM (1:N)
);

CREATE TABLE academic_cycle (
    id         text PRIMARY KEY,
    year       text NOT NULL,
    season     text NOT NULL CHECK (season IN ('Z', 'L')),
    start_date date NOT NULL,
    end_date   date NOT NULL CHECK (end_date > start_date),
    UNIQUE (year, season)
);

CREATE TABLE curriculum_term (
    id            text PRIMARY KEY,
    sem           integer NOT NULL CHECK (sem > 0),
    curriculum_id text NOT NULL REFERENCES curriculum (id)      -- HAS_TERM (1:N)
);

CREATE TABLE taught_in (                                         -- TAUGHT_IN (N:0..1)
    term_id  text PRIMARY KEY REFERENCES curriculum_term (id) ON DELETE CASCADE,
    cycle_id text NOT NULL REFERENCES academic_cycle (id)
);

CREATE TABLE subject (
    code text PRIMARY KEY,
    name text NOT NULL
);

CREATE TABLE subject_ects (                                      -- optional Subject.ects
    subject_code text PRIMARY KEY REFERENCES subject (code) ON DELETE CASCADE,
    ects         integer NOT NULL CHECK (ects >= 0)
);

CREATE TABLE term_subject (                                     -- INCLUDES (N:M)
    term_id      text REFERENCES curriculum_term (id),
    subject_code text REFERENCES subject (code),
    PRIMARY KEY (term_id, subject_code)
);

-- A subject instance has no properties: it is fully identified by its subject and cycle,
-- so in SQL the pair simply is its primary key.
CREATE TABLE subject_instance (
    subject_code text REFERENCES subject (code),                -- INSTANCE_OF (N:1)
    cycle_id     text REFERENCES academic_cycle (id),           -- OFFERED_IN (N:1)
    PRIMARY KEY (subject_code, cycle_id)
);

CREATE TABLE group_type (
    id           text PRIMARY KEY,
    g_type       text NOT NULL,
    weight       double precision NOT NULL CHECK (weight > 0 AND weight <= 1),
    subject_code text NOT NULL,                                  -- HAS_TYPE (1:N)
    cycle_id     text NOT NULL,
    FOREIGN KEY (subject_code, cycle_id) REFERENCES subject_instance (subject_code, cycle_id)
);

-- Classes ---------------------------------------------------------------------
CREATE TABLE room (
    id       text PRIMARY KEY,
    building text NOT NULL,
    room_num text NOT NULL,
    UNIQUE (building, room_num)
);

-- "group" is a reserved word in SQL.
CREATE TABLE class_group (
    id            text PRIMARY KEY,
    number        integer NOT NULL,
    capacity      integer NOT NULL CHECK (capacity > 0),
    weekday       integer NOT NULL CHECK (weekday BETWEEN 1 AND 7),
    start_time    time NOT NULL,
    end_time      time NOT NULL,
    pnp           text NOT NULL CHECK (pnp IN ('P', 'NP', 'ALL')),
    group_type_id text NOT NULL REFERENCES group_type (id),      -- OF_TYPE (N:1)
    UNIQUE (group_type_id, number)        -- natural key that the graph type cannot express
);

CREATE TABLE in_room (                                           -- IN_ROOM (N:0..1)
    group_id text PRIMARY KEY REFERENCES class_group (id) ON DELETE CASCADE,
    room_id  text NOT NULL REFERENCES room (id)
);

CREATE TABLE teaches (                                           -- TEACHES (N:M)
    teacher_idx text REFERENCES teacher (idx),
    group_id    text REFERENCES class_group (id),
    PRIMARY KEY (teacher_idx, group_id)
);

CREATE TABLE works_at (                                          -- WORKS_AT (N:M)
    teacher_idx text REFERENCES teacher (idx),
    faculty_id  text REFERENCES faculty (id),
    PRIMARY KEY (teacher_idx, faculty_id)
);

CREATE TABLE enrolled (                                          -- ENROLLED (N:M)
    student_idx text REFERENCES student (idx),
    term_id     text REFERENCES curriculum_term (id),
    PRIMARY KEY (student_idx, term_id)
);

CREATE TABLE registered_in (                                     -- REGISTERED_IN (N:M) with properties
    student_idx   text REFERENCES student (idx),
    group_id      text REFERENCES class_group (id),
    registered_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (student_idx, group_id)
);

-- Optional REGISTERED_IN.grade: a grade can only exist for an existing registration.
CREATE TABLE grade (
    student_idx text,
    group_id    text,
    grade       numeric(2, 1) NOT NULL CHECK (grade IN (2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0)),
    PRIMARY KEY (student_idx, group_id),
    FOREIGN KEY (student_idx, group_id) REFERENCES registered_in (student_idx, group_id) ON DELETE CASCADE
);

-- Registrations ---------------------------------------------------------------
CREATE TABLE registration (
    id         text PRIMARY KEY,
    name       text NOT NULL,
    reg_type   text NOT NULL,
    cycle_id   text NOT NULL REFERENCES academic_cycle (id),     -- FOR_CYCLE (N:1)
    faculty_id text NOT NULL REFERENCES faculty (id)             -- FOR_FACULTY (N:1)
);

CREATE TABLE registration_turn (
    id              text PRIMARY KEY,
    turn_number     integer NOT NULL,
    date            date NOT NULL,
    start_time      time NOT NULL,
    end_time        time NOT NULL,
    registration_id text NOT NULL REFERENCES registration (id),  -- HAS_TURN (1:N)
    UNIQUE (id, registration_id)          -- target of the composite key in `assigned`
);

CREATE TABLE opens (                                             -- OPENS (N:M)
    registration_id text REFERENCES registration (id),
    group_id        text REFERENCES class_group (id),
    PRIMARY KEY (registration_id, group_id)
);

-- ASSIGNED: at most one turn per registration, enforced by the database
-- (in the graph this rule is checked only by the API).
CREATE TABLE assigned (
    student_idx     text REFERENCES student (idx),
    turn_id         text NOT NULL,
    registration_id text NOT NULL,
    PRIMARY KEY (student_idx, turn_id),
    UNIQUE (student_idx, registration_id),
    FOREIGN KEY (turn_id, registration_id) REFERENCES registration_turn (id, registration_id)
);

-- Opinions --------------------------------------------------------------------
CREATE TABLE opinion (
    id          text PRIMARY KEY,
    grade       numeric(2, 1) NOT NULL CHECK (grade IN (2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0)),
    submit      timestamptz NOT NULL,
    student_idx text NOT NULL REFERENCES student (idx),          -- WRITES (1:N)
    group_id    text NOT NULL REFERENCES class_group (id),       -- ABOUT (N:1)
    teacher_idx text NOT NULL REFERENCES teacher (idx),          -- ABOUT_TEACHER (N:1)
    UNIQUE (student_idx, group_id, teacher_idx)                  -- one opinion per triple
);

CREATE TABLE opinion_content (                                   -- optional Opinion.content
    opinion_id text PRIMARY KEY REFERENCES opinion (id) ON DELETE CASCADE,
    content    text NOT NULL
);

-- Indexes on foreign keys used for traversal in the compared queries.
-- (PostgreSQL indexes primary keys and UNIQUE columns automatically, but not foreign keys.)
CREATE INDEX ON programme (faculty_id);
CREATE INDEX ON curriculum (programme_id);
CREATE INDEX ON curriculum_term (curriculum_id);
CREATE INDEX ON taught_in (cycle_id);
CREATE INDEX ON term_subject (subject_code);
CREATE INDEX ON group_type (subject_code, cycle_id);
CREATE INDEX ON in_room (room_id);
CREATE INDEX ON teaches (group_id);
CREATE INDEX ON enrolled (term_id);
CREATE INDEX ON registered_in (group_id);
CREATE INDEX ON registration_turn (registration_id);
CREATE INDEX ON opens (group_id);
CREATE INDEX ON assigned (turn_id);
CREATE INDEX ON opinion (group_id);
CREATE INDEX ON opinion (teacher_idx);
