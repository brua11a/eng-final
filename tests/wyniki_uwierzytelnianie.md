# Uwierzytelnianie - czas odpowiedzi logowania i limit długości hasła

Data: 2026-11-18. Test: `tests/test_login_timing.py` (uruchomienie: `python tests/test_login_timing.py --n 30`), wykonywany na lokalnym stacku Docker Compose (`https://localhost:8000/api`).

## Cel

1. **Enumeracja kont przez czas odpowiedzi.** `POST /api/login` zwraca tę samą odpowiedź (401 `Invalid email or password`) dla nieistniejącego konta i dla błędnego hasła. Test sprawdza, czy konta nie da się rozpoznać po czasie odpowiedzi. Mierzone są trzy przypadki: istniejące konto z poprawnym hasłem, istniejące konto z błędnym hasłem i nieistniejące konto. Próg: różnica median między dwoma ostatnimi przypadkami poniżej 30 ms.
2. **Hasło dłuższe niż 72 bajty.** bcrypt 5.0.0 odrzuca takie hasła wyjątkiem `ValueError`. Test wysyła `POST /api/admin/users` z hasłem 73-bajtowym (jako administrator, z nieistniejącym `idx`, więc dane się nie zmieniają). Oczekiwany kod to 422.

## Przed poprawką

Liczba prób na przypadek: 30

| Przypadek | Kod | Odpowiedź | Mediana [ms] | Min [ms] | Max [ms] |
| --- | :---: | --- | ---: | ---: | ---: |
| istniejące konto, poprawne hasło | 200 | `(token)` | 185.1 | 183.4 | 207.2 |
| istniejące konto, błędne hasło | 401 | `Invalid email or password` | 183.7 | 182.9 | 190.4 |
| nieistniejące konto | 401 | `Invalid email or password` | 4.0 | 3.6 | 5.7 |

Różnica median (błędne hasło vs nieistniejące konto): 179.7 ms (próg: 30 ms)

POST /api/admin/users z hasłem 73-bajtowym: 500 `{"detail":"Internal server error"}`

Wynik: **oba testy niezaliczone.**

- Dla nieistniejącego konta odpowiedź przychodziła ok. 45 razy szybciej (4 ms zamiast 184 ms), ponieważ bcrypt wykonywał się tylko wtedy, gdy użytkownik o danym adresie istniał. Mimo identycznej treści odpowiedzi czas pozwalał więc jednoznacznie sprawdzić, czy konto istnieje.
- `hash_password()` nie przechwytywał wyjątku `ValueError` z bcrypt, przez co za długie hasło kończyło się błędem 500.

## Poprawki

- `app/graph_backend/auth/deps.py`: przy starcie aplikacji wyliczany jest `DUMMY_PASSWORD_HASH`, czyli skrót losowego hasła o tym samym koszcie (12).
- `app/graph_backend/routers/public.py`: jeśli użytkownik nie istnieje, hasło jest sprawdzane względem `DUMMY_PASSWORD_HASH`. bcrypt wykonuje się więc zawsze, a odpowiedź pozostaje bez zmian (401).
- `app/schemas/auth.py`: walidator `passwd_fits_bcrypt` w `AssignUserRequest` odrzuca hasła dłuższe niż 72 bajty (liczone po zakodowaniu w UTF-8, a nie w znakach) kodem 422, zanim punkt końcowy zostanie wywołany.

## Po poprawce

Liczba prób na przypadek: 30

| Przypadek | Kod | Odpowiedź | Mediana [ms] | Min [ms] | Max [ms] |
| --- | :---: | --- | ---: | ---: | ---: |
| istniejące konto, poprawne hasło | 200 | `(token)` | 183.6 | 182.8 | 189.2 |
| istniejące konto, błędne hasło | 401 | `Invalid email or password` | 183.3 | 182.1 | 189.8 |
| nieistniejące konto | 401 | `Invalid email or password` | 183.2 | 182.1 | 186.4 |

Różnica median (błędne hasło vs nieistniejące konto): 0.0 ms (próg: 30 ms)

POST /api/admin/users z hasłem 73-bajtowym: 422 `{"detail":[{"type":"value_error","loc":["body","passwd"],"msg":"Value error, password cannot be longer than 72 bytes",...}]}`

Wynik: **oba testy zaliczone.** Czasy wszystkich trzech przypadków są takie same w granicach szumu pomiarowego (ok. 183 ms), a za długie hasło jest odrzucane kodem 422 z komunikatem wskazującym pole `passwd`.

## Uwagi

- Poprawka wydłuża logowanie na nieistniejące konto do czasu zwykłego logowania (ok. 180 ms). Jest to zamierzone.
- Hasło dłuższe niż 72 bajty podane przy logowaniu nadal kończy się szybkim 401, bo bcrypt odrzuca je przed liczeniem skrótu. Dzieje się tak jednak niezależnie od tego, czy konto istnieje, więc nie zdradza to istnienia konta.
- Wyniki zależą od maszyny, na której działa stack. Bezwzględne czasy mogą się różnić, ale istotna jest różnica między przypadkami.
