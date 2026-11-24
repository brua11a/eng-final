Liczba prób na przypadek: 30

| Przypadek | Kod | Odpowiedź | Mediana [ms] | Min [ms] | Max [ms] |
| --- | :---: | --- | ---: | ---: | ---: |
| istniejące konto, poprawne hasło | 200 | `(token)` | 183.2 | 181.9 | 196.0 |
| istniejące konto, błędne hasło | 401 | `Invalid email or password` | 182.4 | 181.4 | 183.8 |
| nieistniejące konto | 401 | `Invalid email or password` | 182.2 | 181.4 | 186.2 |

Różnica median (błędne hasło vs nieistniejące konto): 0.2 ms (próg: 30 ms)

POST /api/admin/users z hasłem 73-bajtowym: 422 `{"detail":[{"type":"value_error","loc":["body","passwd"],"msg":"Value error, password cannot be longer than 72 bytes","input":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`
