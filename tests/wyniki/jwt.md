Punkt końcowy: `GET /api/admin/people/next-idx` (rola Admin).

| Token | Oczekiwano | Odpowiedź | Zgodny |
| --- | --- | --- | --- |
| kontrola: poprawny token administratora | 200 | 200 | tak |
| kontrola: poprawny token studenta | 403 Forbidden | 403 Forbidden | tak |
| token studenta z dopisaną rolą Admin, stary podpis | 401 Invalid token | 401 Invalid token | tak |
| rola Admin, algorytm none, bez podpisu | 401 Invalid token | 401 Invalid token | tak |
| rola Admin, podpis innym kluczem | 401 Invalid token | 401 Invalid token | tak |
| podpis kluczem API, algorytm HS512 | 401 Invalid token | 401 Invalid token | tak |
| token wygasły (exp w przeszłości) | 401 Invalid token | 401 Invalid token | tak |
| token bez exp (bezterminowy) | 401 Invalid token | 401 Invalid token | tak |
| token bez iat | 401 Invalid token | 401 Invalid token | tak |
| token bez sub | 401 Invalid token | 401 Invalid token | tak |
| token wydany przed uruchomieniem API | 401 Token revoked | 401 Token revoked | tak |
| nieznana rola | 401 Invalid token | 401 Invalid token | tak |
| pusta lista ról | 401 Invalid token | 401 Invalid token | tak |
| role jako tekst zamiast listy | 401 Invalid token | 401 Invalid token | tak |
| uszkodzony token | 401 Invalid token | 401 Invalid token | tak |
| schemat inny niż Bearer | 401 Not authenticated | 401 Not authenticated | tak |
| brak nagłówka | 401 Not authenticated | 401 Not authenticated | tak |

Wynik: OK
