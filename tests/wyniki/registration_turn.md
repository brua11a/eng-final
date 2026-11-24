## A. Zapis i wypis względem tury

| Przypadek | Metoda | Oczekiwano | Kod | Komunikat | Zgodny |
| --- | --- | --- | --- | --- | --- |
| tura trwa: zapis | `PUT` | 204 | 204 | – | tak |
| tura trwa: ponowny zapis do tej samej grupy (PUT idempotentny) | `PUT` | 204 | 204 | – | tak |
| tura trwa: wypis | `DELETE` | 204 | 204 | – | tak |
| tura trwa: wypis z grupy, do której nie jest zapisany | `DELETE` | 404 | 404 | Registration in this group not found | tak |
| tura trwa: zapis do grupy z innych zapisów (bez przydziału do tury) | `PUT` | 403 | 403 | Group not open to you, or outside your registration turn | tak |
| tura zakończona: zapis | `PUT` | 403 | 403 | Group not open to you, or outside your registration turn | tak |
| tura zakończona: wypis (zapisany wcześniej przez dziekanat) | `DELETE` | 403 | 403 | Group not open to you, or outside your registration turn | tak |
| tura jutro: zapis | `PUT` | 403 | 403 | Group not open to you, or outside your registration turn | tak |

Tury zapisane w bazie (wysłane jako godzina z przesunięciem +01:00):

| Data | Początek | Koniec | Typ |
| --- | --- | --- | --- |
| 2026-11-24 | 08:00:00.000000000 | 20:00:00.000000000 | LOCAL TIME NOT NULL |
| 2026-11-25 | 00:00:00.000000000 | 23:59:59.000000000 | LOCAL TIME NOT NULL |
| 2026-11-25 | 00:00:00.000000000 | 23:59:59.000000000 | LOCAL TIME NOT NULL |
| 2026-11-26 | 08:00:00.000000000 | 20:00:00.000000000 | LOCAL TIME NOT NULL |

## B. Początek tury o 8:00 w strefie Europe/Warsaw

| Data | Czas lokalny + strefa (obecnie) | 08:00+01:00 w czasie polskim (dawniej) | 8:00 czasu polskiego |
| --- | --- | --- | --- |
| 2026-01-15 | 2026-01-15T08:00:00+01:00[Europe/Warsaw] | 2026-01-15T08:00:00+01:00[Europe/Warsaw] | tak |
| 2026-03-28 | 2026-03-28T08:00:00+01:00[Europe/Warsaw] | 2026-03-28T08:00:00+01:00[Europe/Warsaw] | tak |
| 2026-03-29 | 2026-03-29T08:00:00+02:00[Europe/Warsaw] | 2026-03-29T09:00:00+02:00[Europe/Warsaw] | tak |
| 2026-07-01 | 2026-07-01T08:00:00+02:00[Europe/Warsaw] | 2026-07-01T09:00:00+02:00[Europe/Warsaw] | tak |
| 2026-10-24 | 2026-10-24T08:00:00+02:00[Europe/Warsaw] | 2026-10-24T09:00:00+02:00[Europe/Warsaw] | tak |
| 2026-10-25 | 2026-10-25T08:00:00+01:00[Europe/Warsaw] | 2026-10-25T08:00:00+01:00[Europe/Warsaw] | tak |

Wyrażenie występuje w kwerendach `_REGISTER` i `_DEREGISTER`: tak.

Wynik: OK
