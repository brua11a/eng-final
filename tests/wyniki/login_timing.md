Liczba prób na przypadek: 30

| Przypadek | Kod | Odpowiedź | Mediana [ms] | Min [ms] | Max [ms] |
| --- | :---: | --- | ---: | ---: | ---: |
| istniejące konto, poprawne hasło | 200 | `(token)` | 182.9 | 182.3 | 202.3 |
| istniejące konto, błędne hasło | 401 | `Invalid email or password` | 182.7 | 182.2 | 186.8 |
| nieistniejące konto | 401 | `Invalid email or password` | 182.7 | 181.9 | 188.1 |

Różnica median (błędne hasło vs nieistniejące konto): 0.0 ms (próg: 30 ms)

POST /api/admin/users z hasłem 73-bajtowym: 422 `{"detail":[{"type":"value_error","loc":["body","passwd"],"msg":"Value error, password cannot be longer than 72 bytes","input":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`
