API: https://localhost:8000/api. ✗ oznacza wynik niezgodny z macierzą uprawnień.

## A. Role (RBAC)

| Punkt końcowy | Dozwolone role | Bez tokenu | student | prowadzący | administrator | student i prowadzący |
| --- | --- | --- | --- | --- | --- | --- |
| `POST /login` | wszyscy | 422 | – | – | – | – |
| `GET /teachers` | Admin, Student, Teacher | 401 | 200 | 200 | 200 | 200 |
| `GET /subjects` | Admin, Student, Teacher | 401 | 200 | 200 | 200 | 200 |
| `GET /faculties` | Admin, Student, Teacher | 401 | 200 | 200 | 200 | 200 |
| `GET /curricula` | Admin, Student, Teacher | 401 | 200 | 200 | 200 | 200 |
| `GET /subjects/{code}` | Admin, Student, Teacher | 401 | 200 | 200 | 200 | 200 |
| `GET /subjects/{subject_code}/groups` | Admin, Student, Teacher | 401 | 200 | 200 | 200 | 200 |
| `GET /groups/{group_id}` | Admin, Student, Teacher | 401 | 200 | 200 | 200 | 200 |
| `GET /teachers/{idx}` | Admin, Student, Teacher | 401 | 200 | 200 | 200 | 200 |
| `GET /teachers/{idx}/groups` | Admin, Student, Teacher | 401 | 200 | 200 | 200 | 200 |
| `GET /opinions` | Admin, Student, Teacher | 401 | 200 | 200 | 200 | 200 |
| `POST /opinions` | Student | 401 | 422 | 403 | 403 | 422 |
| `GET /me/registrations` | Student | 401 | 200 | 403 | 403 | 200 |
| `GET /me/registrations/{registration_id}/subjects` | Student | 401 | 200 | 403 | 403 | 200 |
| `GET /me/registrations/{registration_id}/groups` | Student | 401 | 200 | 403 | 403 | 200 |
| `PUT /me/registered-groups/{group_id}` | Student | 401 | 403 | 403 | 403 | 403 |
| `DELETE /me/registered-groups/{group_id}` | Student | 401 | 404 | 403 | 403 | 404 |
| `GET /me/enrolments` | Student | 401 | 200 | 403 | 403 | 200 |
| `GET /me/academic-cycles` | Student | 401 | 200 | 403 | 403 | 200 |
| `GET /me/academic-cycles/{cycle_id}` | Student | 401 | 200 | 403 | 403 | 200 |
| `GET /me/registered-groups` | Student | 401 | 200 | 403 | 403 | 200 |
| `GET /students/{student_idx}` | Admin, Teacher | 401 | 403 | 200 | 200 | 200 |
| `GET /me/groups` | Teacher | 401 | 403 | 200 | 403 | 200 |
| `GET /groups/{group_id}/students` | Admin, Teacher | 401 | 403 | 200 | 200 | 200 |
| `PUT /groups/{group_id}/students/{student_idx}/grade` | Admin, Teacher | 401 | 403 | 422 | 422 | 422 |
| `GET /admin/teachers` | Admin | 401 | 403 | 403 | 200 | 403 |
| `POST /admin/teachers` | Admin | 401 | 403 | 403 | 422 | 403 |
| `GET /admin/students` | Admin | 401 | 403 | 403 | 200 | 403 |
| `POST /admin/students` | Admin | 401 | 403 | 403 | 422 | 403 |
| `POST /admin/users` | Admin | 401 | 403 | 403 | 422 | 403 |
| `PATCH /admin/users/{idx}` | Admin | 401 | 403 | 403 | 422 | 403 |
| `DELETE /admin/users/{idx}` | Admin | 401 | 403 | 403 | 404 | 403 |
| `PUT /admin/users/{idx}/roles/{role}` | Admin | 401 | 403 | 403 | 404 | 403 |
| `DELETE /admin/users/{idx}/roles/{role}` | Admin | 401 | 403 | 403 | 404 | 403 |
| `POST /admin/group-types` | Admin | 401 | 403 | 403 | 422 | 403 |
| `GET /admin/groups` | Admin | 401 | 403 | 403 | 200 | 403 |
| `POST /admin/groups` | Admin | 401 | 403 | 403 | 422 | 403 |
| `POST /admin/groups/teachers` | Admin | 401 | 403 | 403 | 422 | 403 |
| `GET /admin/rooms` | Admin | 401 | 403 | 403 | 200 | 403 |
| `POST /admin/rooms` | Admin | 401 | 403 | 403 | 422 | 403 |
| `GET /admin/academic-cycles` | Admin | 401 | 403 | 403 | 200 | 403 |
| `POST /admin/academic-cycles` | Admin | 401 | 403 | 403 | 422 | 403 |
| `PUT /admin/subjects/{code}` | Admin | 401 | 403 | 403 | 422 | 403 |
| `GET /admin/curriculum-terms` | Admin | 401 | 403 | 403 | 200 | 403 |
| `POST /admin/curriculum-terms` | Admin | 401 | 403 | 403 | 422 | 403 |
| `GET /admin/curricula` | Admin | 401 | 403 | 403 | 200 | 403 |
| `POST /admin/curricula` | Admin | 401 | 403 | 403 | 422 | 403 |
| `POST /admin/faculties` | Admin | 401 | 403 | 403 | 422 | 403 |
| `POST /admin/registrations` | Admin | 401 | 403 | 403 | 422 | 403 |
| `GET /admin/programmes` | Admin | 401 | 403 | 403 | 200 | 403 |
| `POST /admin/programmes` | Admin | 401 | 403 | 403 | 422 | 403 |
| `GET /admin/subjects` | Admin | 401 | 403 | 403 | 200 | 403 |
| `POST /admin/admins` | Admin | 401 | 403 | 403 | 422 | 403 |
| `POST /admin/curriculum-terms/subjects` | Admin | 401 | 403 | 403 | 422 | 403 |
| `POST /admin/students/{idx}/enrolments` | Admin | 401 | 403 | 403 | 422 | 403 |
| `POST /admin/registrations/turns/students` | Admin | 401 | 403 | 403 | 422 | 403 |
| `GET /admin/registration-turns` | Admin | 401 | 403 | 403 | 200 | 403 |
| `POST /admin/groups/students` | Admin | 401 | 403 | 403 | 422 | 403 |
| `GET /admin/people/next-idx` | Admin | 401 | 403 | 403 | 200 | 403 |

Punktów końcowych: 59, żądań: 291.

## B. Relacje (ReBAC)

| Przypadek | Żądanie | Oczekiwano | Kod | Zgodny |
| --- | --- | --- | --- | --- |
| prowadzący: studenci własnej grupy | `GET /groups/{g_own}/students` | 200 | 200 | tak |
| prowadzący: studenci cudzej grupy | `GET /groups/{g_foreign}/students` | 403 | 403 | tak |
| prowadzący: ocena w cudzej grupie | `PUT /groups/{g_foreign}/students/{in_foreign}/grade` | 403 | 403 | tak |
| prowadzący: szczegóły swojego studenta | `GET /students/{in_foreign}` | 200 | 200 | tak |
| prowadzący: szczegóły studenta, którego nie uczy | `GET /students/{untaught}` | 403 | 403 | tak |
| administrator: studenci dowolnej grupy | `GET /groups/{g_foreign}/students` | 200 | 200 | tak |
| administrator: szczegóły dowolnego studenta | `GET /students/{untaught}` | 200 | 200 | tak |
| student: szczegóły innego studenta | `GET /students/{in_foreign}` | 403 | 403 | tak |
| student: przedmioty we własnych zapisach | `GET /me/registrations/{reg_mine}/subjects` | 200 | 200 | tak |
| student: przedmioty w cudzych zapisach | `GET /me/registrations/{reg_other}/subjects` | 403 | 403 | tak |
| student: własny semestr | `GET /me/academic-cycles/{cycle_mine}` | 200 | 200 | tak |
| student: cykl, w którym nie studiował | `GET /me/academic-cycles/{subject_cycle}` | 403 | 403 | tak |
| student: opinia o grupie, do której nie należy | `POST /opinions` | 403 | 403 | tak |
| student i prowadzący: studenci własnej grupy | `GET /groups/{g_own}/students` | 200 | 200 | tak |
| student i prowadzący: własne zapisy | `GET /me/registrations/{reg_mine}/subjects` | 200 | 200 | tak |
| student i prowadzący: studenci cudzej grupy | `GET /groups/{g_foreign}/students` | 403 | 403 | tak |

Wynik: OK
