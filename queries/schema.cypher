CYPHER 25 ALTER CURRENT GRAPH TYPE SET {

	(t:Teacher => :Person {
		degree :: STRING NOT NULL,
		working_since :: DATE NOT NULL
	}),

	(st:Student => :Person {
		joined :: ZONED DATETIME NOT NULL
	}),

	(u:User => :Person {
		email :: STRING,
		passwd_hash :: STRING NOT NULL
	}) REQUIRE u.email IS KEY,

	(a:Admin => :Person),

	(i:Inactive => :Person {
		deactivated_at :: ZONED DATETIME NOT NULL
	}),

	CONSTRAINT person_idx FOR (pe:Person) REQUIRE pe.idx IS KEY,
	CONSTRAINT person_identity FOR (pe:Person) REQUIRE (pe.name, pe.surname, pe.phone) IS UNIQUE,
	CONSTRAINT person_idx_type FOR (pe:Person) REQUIRE pe.idx IS :: STRING,
	CONSTRAINT person_name FOR (pe:Person) REQUIRE pe.name IS NOT NULL,
	CONSTRAINT person_name_type FOR (pe:Person) REQUIRE pe.name IS :: STRING,
	CONSTRAINT person_surname FOR (pe:Person) REQUIRE pe.surname IS NOT NULL,
	CONSTRAINT person_surname_type FOR (pe:Person) REQUIRE pe.surname IS :: STRING,
	CONSTRAINT person_phone FOR (pe:Person) REQUIRE pe.phone IS NOT NULL,
	CONSTRAINT person_phone_type FOR (pe:Person) REQUIRE pe.phone IS :: STRING,
	CONSTRAINT person_photo FOR (pe:Person) REQUIRE pe.photo IS :: STRING,

	(o:Opinion => {
		id :: STRING,
		grade :: FLOAT NOT NULL,
		content :: STRING,
		submit :: ZONED DATETIME NOT NULL
	}) REQUIRE o.id IS KEY,

	(g:Group => {
		id :: STRING,
		weekday :: INTEGER NOT NULL,
		number :: INTEGER NOT NULL,
		pnp :: STRING NOT NULL,
		capacity :: INTEGER NOT NULL,
		start_hr :: ZONED TIME NOT NULL,
		end_time :: ZONED TIME NOT NULL
	}) REQUIRE g.id IS KEY,

	(gt:GroupType => {
		id :: STRING,
		g_type :: STRING NOT NULL,
		weight :: FLOAT NOT NULL
	}) REQUIRE gt.id IS KEY,

	(r:Room => {
		id :: STRING,
		building :: STRING NOT NULL,
		room_num :: STRING NOT NULL
	}) REQUIRE r.id IS KEY
	   REQUIRE (r.building, r.room_num) IS UNIQUE,

	(ac:AcademicCycle => {
		id :: STRING,
		year :: STRING NOT NULL,
		season :: STRING NOT NULL
	}) REQUIRE ac.id IS KEY
	   REQUIRE (ac.year, ac.season) IS UNIQUE,

	(su:Subject => {
		code :: STRING,
		name :: STRING NOT NULL,
		ects :: INTEGER
	}) REQUIRE su.code IS KEY,

	(si:SubjectInstance => {
		id :: STRING,
		catalogue_code :: STRING
	}) REQUIRE si.id IS KEY,

	(ct:CurriculumTerm => {
		id :: STRING,
		sem :: INTEGER NOT NULL
	}) REQUIRE ct.id IS KEY,

	(p:Programme => {
		id :: STRING,
		name :: STRING NOT NULL
	}) REQUIRE p.id IS KEY
	   REQUIRE p.name IS UNIQUE,

	(c:Curriculum => {
		id :: STRING,
		intake_year :: STRING NOT NULL
	}) REQUIRE c.id IS KEY,

	(fa:Faculty => {
		id :: STRING,
		name :: STRING NOT NULL,
		full_name :: STRING NOT NULL
	}) REQUIRE fa.id IS KEY,

	(reg:Registration => {
		id :: STRING,
		name :: STRING NOT NULL,
		reg_type :: STRING NOT NULL
	}) REQUIRE reg.id IS KEY,

	(rt:RegistrationTurn => {
		id :: STRING,
		turn_number :: INTEGER NOT NULL,
		date :: DATE NOT NULL,
		start_hr :: ZONED TIME NOT NULL,
		end_time :: ZONED TIME NOT NULL
	}) REQUIRE rt.id IS KEY,

	(asg:TurnAssignment => {
		id :: STRING
	}) REQUIRE asg.id IS KEY,

	(st)-[:WRITES => {}]->(o),
	(st)-[:ENROLLED => {}]->(ct),
	(st)-[:REGISTERED_IN => {
		registered_at :: ZONED DATETIME NOT NULL,
		grade :: FLOAT
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
	(si)-[:INSTANCE_OF => {}]->(su),
	(si)-[:OFFERED_IN => {}]->(ac),
	(si)-[:HAS_GROUP => {}]->(g),
	(su)-[:HAS_TYPE => {}]->(gt),
	(g)-[:OF_TYPE => {}]->(gt),
	(reg)-[:FOR_CYCLE => {}]->(ac),
	(reg)-[:FOR_FACULTY => {}]->(fa),
	(reg)-[:HAS_TURN => {}]->(rt),
	(reg)-[:OPENS => {}]->(g),
	(g)-[:IN_ROOM => {}]->(r),
	(t)-[:WORKS_AT => {}]->(fa),
	(t)-[:TEACHES => {}]->(g)

}
