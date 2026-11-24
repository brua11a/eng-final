## A. Reguły wystawiania opinii

| Przypadek | Oczekiwano | Odpowiedź | Zgodny |
| --- | --- | --- | --- |
| ocena spoza skali (7.0) | 422 | 422 grade: Value error, grade must be one of 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0 | tak |
| ocena spoza skali (4.2) | 422 | 422 grade: Value error, grade must be one of 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0 | tak |
| treść dłuższa niż 1000 znaków | 422 | 422 content: String should have at most 1000 characters | tak |
| student niezapisany do grupy | 403 | 403 Forbidden | tak |
| prowadzący, który nie prowadzi grupy | 403 | 403 Teacher does not teach this group | tak |
| poprawna opinia | 201 | 201 | tak |
| ta sama grupa i prowadzący drugi raz | 409 | 409 Opinion already exists | tak |
| drugi prowadzący tej samej grupy | 201 | 201 | tak |
| inny student, ta sama grupa i prowadzący | 201 | 201 | tak |

## B. Jednoczesne opinie tego samego studenta

| Żądania | Odpowiedzi | Opinii w bazie | Zgodny |
| --- | --- | --- | --- |
| 10 | 201: 1, 409: 9 | 1 | tak |

## C. Odczyt opinii (`GET /opinions?group_id=...`, jako prowadzący)

| Sprawdzenie | Oczekiwano | Wynik | Zgodny |
| --- | --- | --- | --- |
| liczba opinii o grupie | 4 | 4 | tak |
| identyfikatory autorów w odpowiedzi | brak | brak | tak |
| moment wystawienia | sama data | 2026-11-25 | tak |

Pola opinii w odpowiedzi: `content`, `course_code`, `course_name`, `cycle`, `g_type`, `grade`, `group_id`, `id`, `submit`, `teacher`, `teacher_idx`.

Wynik: OK
