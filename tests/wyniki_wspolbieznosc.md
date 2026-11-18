# Współbieżność - zapisy do grup i usuwanie ról

Data: 2026-11-18. Test: `tests/test_concurrent_registration.py` (uruchomienie: `python tests/test_concurrent_registration.py`), wykonywany na lokalnym stacku Docker Compose.

## Cel

Sprawdzenie, czy jednoczesne żądania nie naruszają reguł zapisów (limit miejsc, jedna grupa danego typu) ani zasady „każda osoba ma co najmniej jedną rolę”. Dodatkowo sprawdzono, co się dzieje bez blokad zapisu.

## Przebieg

1. Test tworzy w bazie tymczasowe dane z identyfikatorami `test-…`: rejestrację z turą trwającą w chwili testu, cztery grupy (dwa typy grup, które nie mają żadnych zapisów) oraz osobę z rolami Teacher i Student.
2. Tokeny studentów i administratora są generowane w kontenerze `app` kluczem `JWT_SECRET`, więc studenci nie potrzebują kont.
3. Żądania HTTP są wysyłane z wątków zwalnianych wspólną barierą, czyli w praktyce jednocześnie.
4. Scenariusz kontrolny C wykonuje kwerendę `_REGISTER` bez linii `SET st.idx = st.idx` i `SET g.capacity = g.capacity` bezpośrednio przez sterownik (10 równoległych sesji).
5. Na koniec dane testowe są usuwane (sprawdzono: po teście w bazie nie ma węzłów `test-…`).

## Wyniki

| Scenariusz | Żądania | Odpowiedzi | Stan bazy | Oczekiwano |
| --- | ---: | --- | --- | --- |
| A: 10 studentów, grupa z 3 miejscami | 10 | 204: 3, 409: 7 | 3 zapisanych | 3 zapisanych |
| B: 5 studentów × 2 grupy tego samego typu | 10 | 204: 5, 409: 5 | 1: 5 (grup na studenta: liczba studentów) | każdy w 1 grupie |
| D: odebranie obu ról osobie z dwiema rolami | 2 | 200: 1, 409: 1 | pozostałe role: Teacher | jedna rola |
| C (kontrola): jak A, zapytanie bez blokad | 10 | statusy: ok: 10 | 10 zapisanych | – |

Komunikaty 409:
- A: `Group is full` (7)
- B: `You are already registered in another group of this type for this subject` (5)
- D: `Cannot remove last role` (1)

Test uruchomiono dwukrotnie, z identycznymi wynikami. Scenariusze A, B i D: **zaliczone**.

## Wnioski

- Z blokadami limit miejsc i zasada jednej grupy danego typu są zachowane przy jednoczesnych żądaniach.
- Bez blokad (C) do grupy z 3 miejscami zapisało się 10 studentów. Samo umieszczenie sprawdzenia i zapisu w jednej kwerendzie nie wystarcza przy poziomie izolacji *read committed*.
- Usunięcie roli w transakcji z blokadą osoby nie pozwala odebrać jednocześnie obu ról.
