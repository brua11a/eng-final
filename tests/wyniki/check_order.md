| Żądanie | Punkt końcowy | Wywołujący | Oczekiwano | Odpowiedź | Zgodny |
| --- | --- | --- | --- | --- | --- |
| ocena spoza skali | `PUT groups/…` | bez tokenu | 401 | 401 Not authenticated | tak |
| ocena spoza skali | `PUT groups/…` | student | 403 | 403 Forbidden | tak |
| ocena spoza skali | `PUT groups/…` | administrator | 422 | 422 grade: Value error, grade must be one of 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, | tak |
| wydział bez wymaganych pól | `POST admin/…` | bez tokenu | 401 | 401 Not authenticated | tak |
| wydział bez wymaganych pól | `POST admin/…` | student | 403 | 403 Forbidden | tak |
| wydział bez wymaganych pól | `POST admin/…` | administrator | 422 | 422 full_name: Field required | tak |
| grupa z dniem tygodnia 9 | `POST admin/…` | bez tokenu | 401 | 401 Not authenticated | tak |
| grupa z dniem tygodnia 9 | `POST admin/…` | student | 403 | 403 Forbidden | tak |
| grupa z dniem tygodnia 9 | `POST admin/…` | administrator | 422 | 422 weekday: Input should be less than or equal to 7 | tak |

Wynik: OK
