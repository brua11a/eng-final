| Krok | Oczekiwano | Odpowiedź | Zgodny |
| --- | --- | --- | --- |
| nadanie roli: `PUT /admin/users/279413/roles/Admin` | 200 | 200 | tak |
| logowanie studenta | 200 | 200 | tak |
| `GET /admin/people/next-idx` przed odebraniem roli | 200 | 200 | tak |
| odebranie roli: `DELETE /admin/users/279413/roles/Admin` | 200 | 200 | tak |
| `GET /admin/people/next-idx` po odebraniu roli, stary token | 401 Token revoked | 401 Token revoked | tak |
| `PATCH /admin/users/281056` z `{"active": false}`, stary token | 401 Token revoked | 401 Token revoked | tak |
| ponowne logowanie | 200 | 200 | tak |
| `GET /admin/people/next-idx`, nowy token | 403 | 403 Forbidden | tak |

Role w tokenie: przed odebraniem ['Admin', 'Student'], po ponownym logowaniu ['Student'].

Wynik: OK
