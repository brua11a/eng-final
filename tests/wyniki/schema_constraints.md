Konto bazy danych: `app` (konto API).

## A. Reguły wymuszane przez bazę

| Reguła | Wynik | Kod GQL | Komunikat | Zgodny |
| --- | --- | --- | --- | --- |
| typ właściwości: dzień tygodnia jako tekst | odrzucono | 22N78 | Node(566) with label Group required the property weekday to be of type INTEGER, but was of type STRING. | tak |
| wymagana właściwość: grupa bez limitu miejsc | odrzucono | 22N77 | Node(567) with label Group must have the property capacity | tak |
| typ właściwości: godzina zajęć jako tekst | odrzucono | 22N78 | Node(568) with label Group required the property start_time to be of type LOCAL TIME, but was of type STRING. | tak |
| klucz: grupa z istniejącym identyfikatorem | odrzucono | 22N79 | Node(326) already exists with label Group and property id = '131f00c2-a504-550e-8117-167bd6218535' | tak |
| unikalność złożona: sala (budynek, numer) | odrzucono | 22N79 | Node(191) already exists with label Room and properties building = 'C-14', room_num = '112' | tak |
| unikalność złożona: cykl (rok, semestr) | odrzucono | 22N79 | Node(189) already exists with label AcademicCycle and properties year = '2025/26', season = 'Z' | tak |
| etykieta implikowana: Student bez danych osoby (Person) | odrzucono | 22NB3 | Node(564) with label Student is required to have label Person | tak |
| unikalność osoby: imię, nazwisko i telefon | odrzucono | 22N79 | Node(13) already exists with label Person and properties name = 'Marek', surname = 'Wiśniewski', phone = '610000001' | tak |
| klucz: konto z istniejącym adresem e-mail | odrzucono | 22N79 | Node(0) already exists with label User and property email = 'tomasz.szandala@pwr.edu.pl' | tak |
| wymagana właściwość: Inactive bez momentu dezaktywacji | odrzucono | 22N77 | Node(572) with label Inactive must have the property deactivated_at | tak |
| typ węzła na końcu krawędzi: TEACHES od studenta | odrzucono | 22NB4 | Relationship(6919783026478022982) with type TEACHES requires its start Node(13) to have label Teacher | tak |
| typ węzła na końcu krawędzi: IN_ROOM do przedmiotu | odrzucono | 22NB4 | Relationship(1155191996118204742) with type IN_ROOM requires its end Node(56) to have label Room | tak |
| wymagana właściwość krawędzi: zapis bez momentu zapisu | odrzucono | 22N77 | Relationship(6917542221780615494) with type REGISTERED_IN must have the property registered_at | tak |
| typ właściwości krawędzi: ocena jako tekst | odrzucono | 22N78 | Relationship(6917542221780615494) with type REGISTERED_IN required the property grade to be of type FLOAT, but was of type STRING. | tak |

## B. Reguły pilnowane przez API (baza przyjmuje dane)

| Reguła (gdzie egzekwowana) | Wynik w bazie |
| --- | --- |
| dzień tygodnia spoza 1-7 (Pydantic, 5.3.1) | przyjęto |
| parzystość tygodni spoza P/NP/ALL (Pydantic, 5.3.1) | przyjęto |
| ocena spoza skali 2.0-5.0 (Pydantic, 5.5.4) | przyjęto |
| grupa bez formy zajęć (API, 4.3.7) | przyjęto |
| grupa w dwóch salach (API, 4.3.7) | przyjęto |
| dwie grupy o tym samym numerze w jednej formie zajęć (4.3.3) | przyjęto |
| druga instancja przedmiotu w tym samym cyklu (API, 4.3.2) | przyjęto |
| wagi form zajęć niesumujące się do 1 (API, 4.3.2) | przyjęto |
| Inactive bez etykiety User (API, 5.3.1) | przyjęto |
| student w dwóch turach jednych zapisów (API, 4.3.4) | przyjęto |

Wynik: OK
