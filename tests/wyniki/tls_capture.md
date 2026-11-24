Wysłane żądania (przez nginx): `POST /api/login`, `GET /api/subjects?name=tajny-znacznik-52c478a8`, `GET /api/rel/subjects?name=tajny-znacznik-52c478a8` – kody [200, 200].

## Nagrany ruch

| Połączenie | Port | Dane w segmentach TCP | Wersja TLS | Rekordy TLS z danymi | Jawnie widoczne wartości | Zaszyfrowane |
| --- | --- | --- | --- | --- | --- | --- |
| przeglądarka -> nginx | 443 | 13510 B | TLS 1.3 | 22 | brak | tak |
| nginx -> API | 8000 | 9837 B | TLS 1.3 | 23 | brak | tak |
| API -> Neo4j (Bolt) | 7687 | 7836 B | TLS 1.3 | 24 | brak | tak |
| API -> PostgreSQL | 5432 | 7420 B | TLS 1.3 | 25 | brak | tak |

Szukane wartości: hasło, adres e-mail, znacznik z zapytania, token JWT, Cypher (`MATCH (`), SQL (`SELECT `).

## Kontrola: połączenie przeglądarka -> nginx odszyfrowane kluczami sesji klienta

| Metoda | Adres |
| --- | --- |
| POST | /api/login |
| GET | /api/subjects?name=tajny-znacznik-52c478a8 |
| GET | /api/rel/subjects?name=tajny-znacznik-52c478a8 |

| Wartość widoczna po odszyfrowaniu | Znaleziono |
| --- | --- |
| hasło | tak |
| adres e-mail | tak |
| znacznik z zapytania | tak |

Pliki: `/mnt/storage/INZYNIERKA_FINAL/tests/capture/frontend.pcap`, `/mnt/storage/INZYNIERKA_FINAL/tests/capture/app.pcap`, klucze sesji: `/mnt/storage/INZYNIERKA_FINAL/tests/capture/client-keys.log`.

Wynik: OK
