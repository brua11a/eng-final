| Krok | Oczekiwano | Odpowiedź | Zgodny |
| --- | --- | --- | --- |
| `POST /admin/users` - utworzenie konta | 201 | 201 | tak |
| `POST /login` | 200 | 200 token | tak |
| token studenta: `GET /me/enrolments` | 200 | 200 | tak |
| `PATCH /admin/users/285904` z `{"active": false}` | 200 | 200 | tak |
| `POST /login` | 403 Account inactive | 403 Account inactive | tak |
| żądanie z tokenem wydanym przed dezaktywacją | 401 Token revoked | 401 Token revoked | tak |
| `PATCH /admin/users/285904` z `{"active": true}` | 200 | 200 | tak |
| `POST /login` | 200 | 200 token | tak |
| `DELETE /admin/users/285904` | 204 | 204 | tak |
| `POST /login` | 401 Invalid email or password | 401 Invalid email or password | tak |
| `GET /students/285904` (administrator) - dane osoby | 200 | 200 | tak |
| `DELETE /admin/users/A001` (własne konto administratora) | 409 Cannot remove your own account | 409 Cannot remove your own account | tak |

Wynik: OK
