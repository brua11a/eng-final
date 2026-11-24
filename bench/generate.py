"""Generator danych testowych w zadanej skali, jednocześnie w formacie grafowym i relacyjnym.

Struktura danych odpowiada danym początkowym (import/, sql/data/), ale jej rozmiar wynika z liczby
studentów. Pozostałe wielkości są do niej proporcjonalne:
  - wydziały: max(2, ceil(N / 3000)), po 3 kierunki na wydział,
  - roczniki 2023/24-2026/27 (bieżący cykl: 2026/27 Z), plan studiów na rocznik i kierunek,
    7 semestrów, 4 przedmioty na semestr, wspólne dla wszystkich roczników kierunku,
  - instancja przedmiotu w każdym cyklu, w którym któryś rocznik ma go w planie;
    formy zajęć: wykład (grupy po 200 miejsc) i - w 3 na 4 przedmiotach - laboratorium (po 16),
  - każdy student jest zapisany na wszystkie semestry od pierwszego do bieżącego, do jednej grupy
    każdej formy zajęć; zajęcia z zakończonych cykli mają oceny,
  - prowadzący: jeden na ok. 10 grup, część grup ma dwóch prowadzących,
  - zapisy (Registration) dla każdego wydziału w bieżącym cyklu, tury po 100 studentów,
  - opinia od co drugiego studenta o jednej z jego zakończonych grup.
Wszystkie konta mają hasło "student123" (ten sam skrót bcrypt co w danych początkowych);
konto administratora jest takie jak w danych początkowych.

Dane są deterministyczne (stałe ziarno losowania i identyfikatory UUID v5).

Uruchomienie:
    python bench/generate.py 1000 10000 [--out bench/data]
tworzy bench/data/<N>/import/{nodes,edges}/*.csv oraz bench/data/<N>/sql/*.csv.
"""

import argparse
import csv
import math
import random
import uuid
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NS = uuid.UUID("6f1c1a52-6d43-4e5e-9a43-3c6f3f1b2a10")
INTAKES = ["2023/24", "2024/25", "2025/26", "2026/27"]
CURRENT_CYCLE = ("2026/27", "Z")
SEMS, SUBJECTS_PER_SEM = 7, 4
NAMES = ["Anna", "Piotr", "Maria", "Jan", "Zofia", "Jakub", "Julia", "Kacper", "Lena", "Filip", "Maja", "Antoni",
         "Hanna", "Szymon", "Alicja", "Michał", "Oliwia", "Wojciech", "Natalia", "Mateusz"]
SURNAMES = ["Nowak", "Kowalski", "Wiśniewski", "Wójcik", "Kowalczyk", "Kamiński", "Lewandowski", "Zieliński",
            "Szymański", "Woźniak", "Dąbrowski", "Kozłowski", "Jankowski", "Mazur", "Kwiatkowski", "Krawczyk"]
DEGREES = ["mgr inż.", "dr inż.", "dr hab. inż.", "prof. dr hab. inż."]
COMMENTS = ["Dobrze prowadzone zajęcia.", "Za mało przykładów praktycznych.", "Jasne zasady zaliczenia.",
            "Polecam.", "Materiały mogłyby być aktualniejsze."]


def uid(*parts) -> str:
    return str(uuid.uuid5(NS, "/".join(map(str, parts))))


def seed_hashes() -> tuple[str, list[str]]:
    """Skrót hasła "student123" i wiersz administratora z danych początkowych."""
    with open(ROOT / "import" / "nodes" / "students.csv", newline="") as f:
        student_hash = next(r["passwd_hash"] for r in csv.DictReader(f) if r["idx"] == "279413")
    with open(ROOT / "import" / "nodes" / "admins.csv", newline="") as f:
        admin = next(csv.DictReader(f))
    return student_hash, admin


def cycles() -> list[dict]:
    out = []
    for y in range(2023, 2027):
        year = f"{y}/{str(y + 1)[2:]}"
        out.append({"id": uid("cycle", year, "Z"), "year": year, "season": "Z",
                    "start_date": f"{y}-10-01", "end_date": f"{y + 1}-02-15"})
        out.append({"id": uid("cycle", year, "L"), "year": year, "season": "L",
                    "start_date": f"{y + 1}-03-01", "end_date": f"{y + 1}-06-30"})
    return out


def generate(n: int) -> dict[str, list[dict]]:
    rnd = random.Random(n)
    student_hash, admin = seed_hashes()
    t = defaultdict(list)  # tabele w układzie relacyjnym; pliki grafowe powstają z nich niżej

    cyc = cycles()
    t["academic_cycle"] = cyc
    cycle_index = {(c["year"], c["season"]): i for i, c in enumerate(cyc)}
    current = cycle_index[CURRENT_CYCLE]

    people = []  # (idx, name, surname, phone)
    phone = iter(range(500_000_000, 999_999_999))

    def person(idx):
        row = {"idx": idx, "name": rnd.choice(NAMES), "surname": rnd.choice(SURNAMES), "phone": str(next(phone))}
        t["person"].append(row)
        if rnd.random() < 0.2:
            t["person_photo"].append({"idx": idx, "photo": f"{idx}.jpg"})
        return row

    # Administrator z danych początkowych
    t["person"].append({k: admin[k] for k in ("idx", "name", "surname", "phone")})
    t["admin"].append({"idx": admin["idx"]})
    t["app_user"].append({"idx": admin["idx"], "email": admin["email"], "passwd_hash": admin["passwd_hash"]})

    faculties = max(2, math.ceil(n / 3000))
    cohorts = []  # (faculty, programme, curriculum, intake index)
    for f in range(faculties):
        fid = uid("faculty", f)
        t["faculty"].append({"id": fid, "name": f"W{f + 1}", "full_name": f"Wydział {f + 1}"})
        for r in range(40):
            t["room"].append({"id": uid("room", f, r), "building": f"W{f + 1}-{r // 10}", "room_num": str(100 + r)})
        for p in range(3):
            pid = uid("programme", f, p)
            t["programme"].append({"id": pid, "name": f"Kierunek {f + 1}.{p + 1}", "faculty_id": fid})
            subjects = []
            for sem in range(1, SEMS + 1):
                for s in range(SUBJECTS_PER_SEM):
                    code = f"W{f + 1:02d}P{p + 1}-S{sem}{s}"
                    t["subject"].append({"code": code, "name": f"Przedmiot {sem}.{s + 1} ({f + 1}.{p + 1})"})
                    t["subject_ects"].append({"subject_code": code, "ects": rnd.choice([2, 3, 4, 5, 6])})
                    subjects.append((sem, code, s != 3))  # co czwarty przedmiot bez laboratorium
            for i, intake in enumerate(INTAKES):
                cid = uid("curriculum", f, p, intake)
                t["curriculum"].append({"id": cid, "intake_year": intake, "programme_id": pid})
                cohorts.append((f, pid, cid, i, subjects))
                for sem in range(1, SEMS + 1):
                    tid = uid("term", cid, sem)
                    t["curriculum_term"].append({"id": tid, "sem": sem, "curriculum_id": cid})
                    ci = 2 * i + sem - 1
                    if ci < len(cyc):
                        t["taught_in"].append({"term_id": tid, "cycle_id": cyc[ci]["id"]})
                    for sm, code, _ in subjects:
                        if sm == sem:
                            t["term_subject"].append({"term_id": tid, "subject_code": code})

    # Studenci: równo między kohorty
    per = [n // len(cohorts) + (1 if k < n % len(cohorts) else 0) for k in range(len(cohorts))]
    students_of = {}
    next_idx = 300000
    for k, (f, pid, cid, i, subjects) in enumerate(cohorts):
        ids = []
        for _ in range(per[k]):
            idx = str(next_idx)
            next_idx += 1
            person(idx)
            t["student"].append({"idx": idx, "joined": f"{INTAKES[i][:4]}-10-01T00:00:00+02:00"})
            t["app_user"].append({"idx": idx, "email": f"{idx}@student.example.edu", "passwd_hash": student_hash})
            ids.append(idx)
        students_of[k] = ids

    # Instancje, formy zajęć, grupy i zapisy studentów
    groups_of_faculty_cycle = defaultdict(list)
    past_groups_of_student = defaultdict(list)
    teacher_groups = defaultdict(list)  # wydział -> grupy
    for k, (f, pid, cid, i, subjects) in enumerate(cohorts):
        current_sem = current - 2 * i + 1
        for sem in range(1, min(current_sem, SEMS) + 1):
            ci = 2 * i + sem - 1
            cycle = cyc[ci]
            t["enrolled"] += [{"student_idx": s, "term_id": uid("term", cid, sem)} for s in students_of[k]]
            for sm, code, has_lab in subjects:
                if sm != sem or not students_of[k]:
                    continue
                t["subject_instance"].append({"subject_code": code, "cycle_id": cycle["id"]})
                types = [("W", 0.5 if has_lab else 1.0, 200)] + ([("L", 0.5, 16)] if has_lab else [])
                for g_type, weight, cap in types:
                    gtid = uid("group_type", code, cycle["id"], g_type)
                    t["group_type"].append({"id": gtid, "g_type": g_type, "weight": weight,
                                            "subject_code": code, "cycle_id": cycle["id"]})
                    count = math.ceil(len(students_of[k]) / cap)
                    gids = []
                    for g in range(count):
                        gid = uid("group", gtid, g)
                        start = rnd.choice([8, 10, 12, 14, 16])
                        t["class_group"].append({
                            "id": gid, "number": g + 1, "capacity": cap, "weekday": rnd.randint(1, 5),
                            "start_time": f"{start:02d}:15:00", "end_time": f"{start + 1:02d}:55:00",
                            "pnp": rnd.choice(["ALL", "ALL", "P", "NP"]), "group_type_id": gtid})
                        t["in_room"].append({"group_id": gid, "room_id": uid("room", f, rnd.randrange(40))})
                        gids.append(gid)
                        groups_of_faculty_cycle[(f, ci)].append(gid)
                        teacher_groups[f].append(gid)
                    for j, s in enumerate(students_of[k]):
                        gid = gids[j * count // len(students_of[k])]
                        reg_at = f"{cycle['start_date']}T08:{j % 60:02d}:00+02:00"
                        t["registered_in"].append({"student_idx": s, "group_id": gid, "registered_at": reg_at})
                        if ci < current:
                            grade = rnd.choices([2.0, 3.0, 3.5, 4.0, 4.5, 5.0], [5, 20, 20, 25, 15, 15])[0]
                            t["grade"].append({"student_idx": s, "group_id": gid, "grade": grade})
                            past_groups_of_student[s].append((gid, cycle))

    # Prowadzący
    group_teachers = defaultdict(list)
    for f, gids in teacher_groups.items():
        teachers = [f"T{f + 1:02d}{x:04d}" for x in range(math.ceil(len(gids) / 10))]
        for idx in teachers:
            person(idx)
            t["teacher"].append({"idx": idx, "degree": rnd.choice(DEGREES), "working_since": f"{rnd.randint(1990, 2022)}-10-01"})
            t["works_at"].append({"teacher_idx": idx, "faculty_id": uid("faculty", f)})
            t["app_user"].append({"idx": idx, "email": f"{idx.lower()}@example.edu", "passwd_hash": student_hash})
        for j, gid in enumerate(gids):
            chosen = [teachers[j % len(teachers)]]
            if rnd.random() < 0.1 and len(teachers) > 1:
                chosen.append(teachers[(j + 1) % len(teachers)])
            for idx in chosen:
                t["teaches"].append({"teacher_idx": idx, "group_id": gid})
                group_teachers[gid].append(idx)

    # Zapisy w bieżącym cyklu: jedna na wydział, tury po 100 studentów
    cyc_now = cyc[current]
    for f in range(faculties):
        rid = uid("registration", f, current)
        t["registration"].append({"id": rid, "name": f"W{f + 1} - zapisy {cyc_now['year']} {cyc_now['season']}",
                                  "reg_type": "zapisowa", "cycle_id": cyc_now["id"], "faculty_id": uid("faculty", f)})
        t["opens"] += [{"registration_id": rid, "group_id": g} for g in groups_of_faculty_cycle[(f, current)]]
        students = [s for k, c in enumerate(cohorts) if c[0] == f for s in students_of[k]]
        for turn in range(math.ceil(len(students) / 100)):
            tid = uid("turn", rid, turn)
            h = 8 + turn // 4
            m = (turn % 4) * 15
            t["registration_turn"].append({"id": tid, "turn_number": turn, "date": "2026-09-20",
                                           "start_time": f"{h:02d}:{m:02d}:00", "end_time": f"{h + 1:02d}:{m:02d}:00",
                                           "registration_id": rid})
            t["assigned"] += [{"student_idx": s, "turn_id": tid, "registration_id": rid}
                              for s in students[turn * 100:(turn + 1) * 100]]

    # Opinie
    for s, groups in past_groups_of_student.items():
        if rnd.random() < 0.5:
            gid, cycle = rnd.choice(groups)
            oid = uid("opinion", s, gid)
            t["opinion"].append({"id": oid, "grade": rnd.choice([2.0, 3.0, 3.5, 4.0, 4.5, 5.0]),
                                 "submit": f"{cycle['end_date']}T12:00:00+01:00", "student_idx": s,
                                 "group_id": gid, "teacher_idx": group_teachers[gid][0]})
            if rnd.random() < 0.7:
                t["opinion_content"].append({"opinion_id": oid, "content": rnd.choice(COMMENTS)})
    t["inactive"] = []
    return t


SQL_COLUMNS = {  # kolejność kolumn jak w sql/01_schema.sql (COPY ... HEADER match)
    "person": "idx,name,surname,phone", "person_photo": "idx,photo", "student": "idx,joined",
    "teacher": "idx,degree,working_since", "admin": "idx", "app_user": "idx,email,passwd_hash",
    "inactive": "idx,deactivated_at", "faculty": "id,name,full_name", "programme": "id,name,faculty_id",
    "curriculum": "id,intake_year,programme_id", "academic_cycle": "id,year,season,start_date,end_date",
    "curriculum_term": "id,sem,curriculum_id", "taught_in": "term_id,cycle_id", "subject": "code,name",
    "subject_ects": "subject_code,ects", "term_subject": "term_id,subject_code",
    "subject_instance": "subject_code,cycle_id", "group_type": "id,g_type,weight,subject_code,cycle_id",
    "room": "id,building,room_num",
    "class_group": "id,number,capacity,weekday,start_time,end_time,pnp,group_type_id",
    "in_room": "group_id,room_id", "teaches": "teacher_idx,group_id", "works_at": "teacher_idx,faculty_id",
    "enrolled": "student_idx,term_id", "registered_in": "student_idx,group_id,registered_at",
    "grade": "student_idx,group_id,grade", "registration": "id,name,reg_type,cycle_id,faculty_id",
    "registration_turn": "id,turn_number,date,start_time,end_time,registration_id",
    "opens": "registration_id,group_id", "assigned": "student_idx,turn_id,registration_id",
    "opinion": "id,grade,submit,student_idx,group_id,teacher_idx", "opinion_content": "opinion_id,content",
}


def graph_files(t: dict) -> dict[str, tuple[str, list[dict]]]:
    """Te same dane w układzie plików import/ (węzły i krawędzie)."""
    by = lambda table, key: {r[key]: r for r in t[table]}
    person = by("person", "idx")
    photo = {r["idx"]: r["photo"] for r in t["person_photo"]}
    user = by("app_user", "idx")
    ects = {r["subject_code"]: r["ects"] for r in t["subject_ects"]}
    content = {r["opinion_id"]: r["content"] for r in t["opinion_content"]}
    grades = {(r["student_idx"], r["group_id"]): r["grade"] for r in t["grade"]}
    p = lambda idx: person[idx]
    u = lambda idx, k: user.get(idx, {}).get(k, "")
    return {
        "nodes/students.csv": ("idx,name,surname,phone,photo,joined,email,passwd_hash", [
            {**p(r["idx"]), "photo": photo.get(r["idx"], ""), "joined": r["joined"],
             "email": u(r["idx"], "email"), "passwd_hash": u(r["idx"], "passwd_hash")} for r in t["student"]]),
        "nodes/teachers.csv": ("idx,name,surname,phone,degree,working_since,email,passwd_hash", [
            {**p(r["idx"]), **r, "email": u(r["idx"], "email"), "passwd_hash": u(r["idx"], "passwd_hash")}
            for r in t["teacher"]]),
        "nodes/admins.csv": ("idx,name,surname,phone,email,passwd_hash", [
            {**p(r["idx"]), "email": u(r["idx"], "email"), "passwd_hash": u(r["idx"], "passwd_hash")} for r in t["admin"]]),
        "nodes/faculties.csv": ("id,name,full_name", t["faculty"]),
        "nodes/programmes.csv": ("id,name", t["programme"]),
        "nodes/curriculums.csv": ("id,intake_year", t["curriculum"]),
        "nodes/terms.csv": ("id,sem", t["curriculum_term"]),
        "nodes/academic_cycles.csv": ("id,year,season,start_date,end_date", t["academic_cycle"]),
        "nodes/subjects.csv": ("code,name,ects", [{**r, "ects": ects.get(r["code"], "")} for r in t["subject"]]),
        "nodes/rooms.csv": ("id,building,room_num", t["room"]),
        "nodes/group_types.csv": ("id,g_type,weight", t["group_type"]),
        "nodes/groups.csv": ("id,weekday,number,pnp,capacity,start_time,end_time", t["class_group"]),
        "nodes/registrations.csv": ("id,name,reg_type", t["registration"]),
        "nodes/registration_turns.csv": ("id,turn_number,date,start_time,end_time", t["registration_turn"]),
        "nodes/opinions.csv": ("id,grade,content,submit", [{**r, "content": content.get(r["id"], "")} for r in t["opinion"]]),
        "edges/programme_faculties.csv": ("programme_id,faculty_id", [{"programme_id": r["id"], "faculty_id": r["faculty_id"]} for r in t["programme"]]),
        "edges/programme_curriculums.csv": ("programme_id,curriculum_id", [{"programme_id": r["programme_id"], "curriculum_id": r["id"]} for r in t["curriculum"]]),
        "edges/curriculum_terms.csv": ("curriculum_id,term_id", [{"curriculum_id": r["curriculum_id"], "term_id": r["id"]} for r in t["curriculum_term"]]),
        "edges/term_cycles.csv": ("term_id,cycle_id", t["taught_in"]),
        "edges/term_subjects.csv": ("term_id,subject_code", t["term_subject"]),
        "edges/subject_instances.csv": ("subject_code,cycle_id", t["subject_instance"]),
        "edges/instance_group_types.csv": ("subject_code,cycle_id,group_type_id", [
            {"subject_code": r["subject_code"], "cycle_id": r["cycle_id"], "group_type_id": r["id"]} for r in t["group_type"]]),
        "edges/group_of_type.csv": ("group_id,group_type_id", [{"group_id": r["id"], "group_type_id": r["group_type_id"]} for r in t["class_group"]]),
        "edges/group_rooms.csv": ("group_id,room_id", t["in_room"]),
        "edges/teacher_group.csv": ("teacher_idx,group_id", t["teaches"]),
        "edges/teacher_faculty.csv": ("teacher_idx,faculty_id", t["works_at"]),
        "edges/student_enrolled.csv": ("student_idx,term_id", t["enrolled"]),
        "edges/student_registered.csv": ("student_idx,group_id,registered_at,grade", [
            {**r, "grade": grades.get((r["student_idx"], r["group_id"]), "")} for r in t["registered_in"]]),
        "edges/registration_for_cycle.csv": ("registration_id,cycle_id", [{"registration_id": r["id"], "cycle_id": r["cycle_id"]} for r in t["registration"]]),
        "edges/registration_for_faculty.csv": ("registration_id,faculty_id", [{"registration_id": r["id"], "faculty_id": r["faculty_id"]} for r in t["registration"]]),
        "edges/registration_has_turn.csv": ("registration_id,turn_id", [{"registration_id": r["registration_id"], "turn_id": r["id"]} for r in t["registration_turn"]]),
        "edges/registration_groups.csv": ("registration_id,group_id", t["opens"]),
        "edges/turn_assignments.csv": ("student_idx,turn_id", t["assigned"]),
        "edges/opinion_writes.csv": ("opinion_id,student_idx", [{"opinion_id": r["id"], "student_idx": r["student_idx"]} for r in t["opinion"]]),
        "edges/opinion_about_group.csv": ("opinion_id,group_id", [{"opinion_id": r["id"], "group_id": r["group_id"]} for r in t["opinion"]]),
        "edges/opinion_about_teacher.csv": ("opinion_id,teacher_idx", [{"opinion_id": r["id"], "teacher_idx": r["teacher_idx"]} for r in t["opinion"]]),
    }


def write(path: Path, header: str, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = header.split(",")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scales", nargs="+", type=int, help="liczby studentów")
    parser.add_argument("--out", type=Path, default=ROOT / "bench" / "data")
    args = parser.parse_args()
    for n in args.scales:
        t = generate(n)
        base = args.out / str(n)
        for table, header in SQL_COLUMNS.items():
            write(base / "sql" / f"{table}.csv", header, t[table])
        for name, (header, rows) in graph_files(t).items():
            write(base / "import" / name, header, rows)
        print(f"{n}: " + ", ".join(f"{k} {len(t[k])}" for k in
              ("person", "class_group", "registered_in", "grade", "teaches", "opinion", "assigned")))


if __name__ == "__main__":
    main()
