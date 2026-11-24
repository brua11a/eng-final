## Porty wystawione na hosta

| Port | Usługa | TLS z weryfikacją (wersja, szyfr) | Obca nazwa hosta | Żądanie bez TLS | TLS 1.2 (informacyjnie) |
| --- | --- | --- | --- | --- | --- |
| 5173 | nginx: klient webowy i proxy API | TLSv1.3, TLS_AES_256_GCM_SHA384 | odrzucona | HTTP/1.1 400 Bad Request | przyjęte |
| 8000 | API (uvicorn) | TLSv1.3, TLS_AES_256_GCM_SHA384 | odrzucona | połączenie zamknięte bez odpowiedzi | przyjęte |
| 7473 | Neo4j: konsola HTTPS | TLSv1.3, TLS_AES_128_GCM_SHA256 | odrzucona | odpowiedź w protokole TLS (alert/handshake) | przyjęte |
| 7687 | Neo4j: Bolt | TLSv1.3, TLS_AES_128_GCM_SHA256 | odrzucona | połączenie zamknięte bez odpowiedzi | przyjęte |
| 5432 | PostgreSQL | TLSv1.3, TLS_AES_256_GCM_SHA384 | odrzucona | błąd PostgreSQL: pg_hba.conf rejects connection for host "172.21.0.1", user "app", data | odrzucone |

## Adresy, na których opublikowano porty

| Serwis | Adres | Tylko localhost |
| --- | --- | --- |
| app | 127.0.0.1:8000 | tak |
| frontend | 127.0.0.1:5173 | tak |
| neo4j | 127.0.0.1:7473 | tak |
| neo4j | 127.0.0.1:7687 | tak |
| postgres | 127.0.0.1:5432 | tak |

## Połączenia w sieci Dockera (z kontenera app)

| Próba | Wynik |
| --- | --- |
| API -> Neo4j pod adresem IP (172.21.0.2), bolt+s | odrzucono: [SSLCertVerificationError] Connection Failed. Please ensure  |
| API -> Neo4j bez TLS (bolt://) | odrzucono: Connection to 172.21.0.2:7687 closed with incomplete handshake response |
| API -> PostgreSQL pod adresem IP (172.21.0.3), verify-full | odrzucono: server certificate for "postgres" (and 1 other name) does not match host name "172.21.0.3" |
| API -> PostgreSQL bez TLS (sslmode=disable) | odrzucono: FATAL:  pg_hba.conf rejects connection for host "172.21.0.4", user "app", database "usos", no encryption |

Wynik: OK
