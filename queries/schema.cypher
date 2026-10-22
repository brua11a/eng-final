CYPHER 25 ALTER CURRENT GRAPH TYPE SET {

	(t:Teacher => {
		idx :: STRING,
		name :: STRING NOT NULL,
		surname :: STRING NOT NULL,
		phone :: STRING NOT NULL,
		degree :: STRING NOT NULL,
		photo :: STRING,
		working_since :: DATE NOT NULL
	}) REQUIRE t.idx IS KEY
  	REQUIRE (t.name, t.surname, t.phone) IS UNIQUE,

	(st:Student => {
		idx :: STRING,
		name :: STRING NOT NULL,
		surname :: STRING NOT NULL,
		phone :: STRING NOT NULL,
		photo :: STRING,
		joined :: ZONED DATETIME NOT NULL,
		avg_grade :: FLOAT
	}) REQUIRE st.idx IS KEY
    REQUIRE (st.name, st.surname, st.phone) IS UNIQUE,

	(u:User => {
		email :: STRING,
		passwd_hash :: STRING NOT NULL
	}) REQUIRE u.email IS KEY,

	(a:Admin => {
		kind :: STRING NOT NULL
	}),

	(o:Opinion => {
		id :: INTEGER,
		grade :: FLOAT NOT NULL,
		content :: STRING,
		submit :: ZONED DATETIME NOT NULL
	}) REQUIRE o.id IS KEY,

	(g:Group => {
		id :: INTEGER,
		weekday :: INTEGER NOT NULL,
		g_type :: STRING NOT NULL,
		number :: INTEGER NOT NULL,
		pnp :: STRING NOT NULL,
		capacity :: INTEGER NOT NULL,
		start_hr :: ZONED TIME NOT NULL,
		end_time :: ZONED TIME NOT NULL
	}) REQUIRE g.id IS KEY,

	(r:Room => {
		id :: INTEGER,
		building :: STRING NOT NULL,
		room_num :: STRING NOT NULL
	}) REQUIRE r.id IS KEY
	   REQUIRE (r.building, r.room_num) IS UNIQUE,

	(ac:AcademicCycle => {
		id :: INTEGER,
		year :: STRING NOT NULL,
		season :: STRING NOT NULL
	}) REQUIRE ac.id IS KEY
	   REQUIRE (ac.year, ac.season) IS UNIQUE,

	(su:Subject => {
		code :: STRING,
		name :: STRING NOT NULL,
		ects :: INTEGER
	}) REQUIRE su.code IS KEY,

	(ct:CurriculumTerm => {
		id :: INTEGER,
		sem :: INTEGER NOT NULL
	}) REQUIRE ct.id IS KEY,

	(p:Programme => {
		id :: INTEGER,
		name :: STRING NOT NULL
	}) REQUIRE p.id IS KEY
	   REQUIRE p.name IS UNIQUE,

	(c:Curriculum => {
		id :: INTEGER,
		intake_year :: STRING NOT NULL
	}) REQUIRE c.id IS KEY,

	(fa:Faculty => {
		id :: INTEGER,
		name :: STRING NOT NULL,
		full_name :: STRING NOT NULL
	}) REQUIRE fa.id IS KEY,

	(reg:Registration => {
		id :: INTEGER,
		name :: STRING NOT NULL,
		reg_type :: STRING NOT NULL
	}) REQUIRE reg.id IS KEY,

	(rt:RegistrationTurn => {
		id :: INTEGER,
		turn_number :: INTEGER NOT NULL,
		date :: DATE NOT NULL,
		start_hr :: ZONED TIME NOT NULL,
		end_time :: ZONED TIME NOT NULL
	}) REQUIRE rt.id IS KEY,

	(asg:TurnAssignment => {
		id :: INTEGER
	}) REQUIRE asg.id IS KEY,

	(st)-[:WRITES => {}]->(o),
	(st)-[:ENROLLED => {}]->(ct),
	(st)-[:REGISTERED_IN => {
		registered_at :: ZONED DATETIME NOT NULL
	}]->(g),
	(st)-[:ASSIGNED => {}]->(asg),
	(asg)-[:FOR_TURN => {}]->(rt),
	(asg)-[:FOR_CURRICULUM => {}]->(c),
	(o)-[:ABOUT => {}]->(g),
	(p)-[:HAS_CURRICULUM => {}]->(c),
	(p)-[:OFFERED_BY => {}]->(fa),
	(c)-[:HAS_TERM => {}]->(ct),
	(ct)-[:INCLUDES => {}]->(su),
	(ct)-[:TAUGHT_IN => {}]->(ac),
	(g)-[:OF_SUBJECT => {}]->(su),
	(reg)-[:FOR_CYCLE => {}]->(ac),
	(reg)-[:FOR_FACULTY => {}]->(fa),
	(reg)-[:HAS_TURN => {}]->(rt),
	(reg)-[:OPENS => {}]->(g),
	(g)-[:IN_ROOM => {}]->(r),
	(t)-[:WORKS_AT => {}]->(fa),
	(t)-[:TEACHES => {}]->(g)

}
