| Przypadek | Oczekiwano | Wynik | Zgodny |
| --- | --- | --- | --- |
| jedna forma zajęć | 4.0 | 4.0 | tak |
| średnia ważona form zajęć: 0,7·5.0 + 0,3·4.0 | 4.7 | 4.7 | tak |
| ocena negatywna z jednej formy: 0,7·5.0 + 0,3·2.0 daje 2.0, nie 4.1 | 2.0 | 2.0 | tak |
| średnia ważona ECTS: (5·4.0 + 2·5.0) / 7 | 4.286 | 4.286 | tak |
| poprawa przedmiotu: liczy się późniejsze podejście | 4.5 | 4.5 | tak |
| kolejność cykli: semestr letni po zimowym tego samego roku | 3.0 | 3.0 | tak |
| niepełne podejście (brak oceny z laboratorium) jest pomijane | 3.5 | 3.5 | tak |
| brak żadnej pełnej oceny | None | None | tak |
| przedmiot bez punktów ECTS nie wchodzi do średniej | 3.0 | 3.0 | tak |
| dwie grupy tej samej formy w jednym podejściu: średnia z nich | 4.0 | 4.0 | tak |
| wagi niesumujące się do 1 są normalizowane: (2·5.0 + 2·3.0) / 4 | 4.0 | 4.0 | tak |

Test przez API: student 285902, średnia przed wystawieniem oceny None; po `PUT .../grade` z oceną 3.0 (kod 200) `GET /students/285902` zwraca 3.75, funkcja dla tych samych danych 3.75 – zgodne: tak. Ocena została potem usunięta.

Wynik: OK
