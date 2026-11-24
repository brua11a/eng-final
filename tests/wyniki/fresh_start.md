Klon: `/tmp/thesis-fresh-djtqh5jf/repo` (projekt Compose `thesis-fresh`), usunięty po teście: tak.

| Krok | Wynik | Zgodny | Uwagi |
| --- | --- | --- | --- |
| 1. klon, .env, certs.sh | certs.sh: kod 0 | tak | – |
| 2. pierwsze uruchomienie na pustych wolumenach | logowanie przez nginx: 200 po 27 s; {'nodes': 563, 'edges': 1448, 'tables': 32, 'rows': 1635} | tak | – |
| 3. ponowne uruchomienie (init wykonuje import drugi raz) | logowanie: 200; {'nodes': 563, 'edges': 1448, 'tables': 32, 'rows': 1635} | tak | liczby bez zmian |
| 4. zmiana NEO4J_APP_PASSWORD w .env | logowanie: 200 | tak | – |
| 5. zmiana PG_APP_PASSWORD w .env (bez usunięcia wolumenu pg_data) | logowanie: None; kontener app: exited (Exited (3) 34 seconds ago) | tak | API nie startuje: password authentication failed (oczekiwane, 6.3) |

Wynik: OK
