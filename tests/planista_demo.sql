-- Demonstracja pracy planisty PostgreSQL (do zrzutów ekranu w DBeaver).
-- Dane: skala 10 000 studentów (bench/data/10000), baza usos.
-- Uruchamiać polecenia POJEDYNCZO (Ctrl+Enter), w jednym edytorze SQL (jedna sesja):
-- polecenia przygotowane (PREPARE) istnieją tylko w sesji, w której je utworzono.

-- 0. Sprzątanie po poprzednim uruchomieniu i świeże statystyki dla planisty
DEALLOCATE ALL;
ANALYZE;

-- =====================================================================
-- Część 1. Plan dla konkretnych parametrów a plan ogólny
-- =====================================================================

-- 1a. Zapytanie z wartością wpisaną wprost: planista zna wartość i szacuje, ile wierszy pasuje
--     (rows=4), więc wybiera indeks. W planie widać literał: Index Cond: (teacher_idx = 'T010000')
EXPLAIN (ANALYZE, SUMMARY)
SELECT o.id, o.grade FROM opinion o WHERE o.teacher_idx = 'T010000' ORDER BY o.submit DESC;

-- 1b. To samo jako polecenie przygotowane, tak jak wykonuje je API (psycopg robi PREPARE
--     po 5 wykonaniach zapytania)
PREPARE opinie(text) AS
SELECT o.id, o.grade FROM opinion o WHERE o.teacher_idx = $1 ORDER BY o.submit DESC;

-- 1c. Wykonać 6 razy. Przy wykonaniach 1-5 w planie jest literał 'T010000' (plan dla
--     konkretnych parametrów, planowany za każdym razem). Przy 6. wykonaniu PostgreSQL porównuje
--     koszt planu ogólnego ze średnim kosztem poprzednich planów i przechodzi na plan ogólny:
--     w planie pojawia się Index Cond: (teacher_idx = $1) - plan nie zna już wartości parametru.
EXPLAIN (ANALYZE, SUMMARY) EXECUTE opinie('T010000');

-- 1d. Liczniki planów: po 6 wykonaniach custom_plans = 5, generic_plans = 1
SELECT name, generic_plans, custom_plans, statement FROM pg_prepared_statements;

-- =====================================================================
-- Część 2. Dlaczego warunek "$1 IS NULL OR ..." nie pozwala użyć indeksu w planie ogólnym
-- =====================================================================

-- 2a. Pierwotna wersja filtra (jeden warunek dla obu opcjonalnych parametrów)
PREPARE opinie_stara(text, text) AS
SELECT o.id, o.grade FROM opinion o
WHERE ($1::text IS NULL OR o.teacher_idx = $1)
  AND ($2::text IS NULL OR o.group_id = $2)
ORDER BY o.submit DESC;

-- 2b. Plan dla konkretnych parametrów: planista zna wartości, upraszcza warunek
--     ('T010000' IS NULL jest fałszem, NULL IS NULL prawdą) i używa indeksu na teacher_idx
SET plan_cache_mode = force_custom_plan;
EXPLAIN (ANALYZE, SUMMARY) EXECUTE opinie_stara('T010000', NULL);

-- 2c. Plan ogólny tego samego zapytania: plan musi działać dla każdej wartości, także NULL,
--     więc nie może zacząć od indeksu - Seq Scan na całej tabeli opinion z filtrem OR
SET plan_cache_mode = force_generic_plan;
EXPLAIN (ANALYZE, SUMMARY) EXECUTE opinie_stara('T010000', NULL);

-- 2d. Wersja po poprawce (osobne zapytanie dla prowadzącego) - plan ogólny używa indeksu
EXPLAIN (ANALYZE, SUMMARY) EXECUTE opinie('T010000');

-- 2e. Przywrócenie ustawienia domyślnego (planista sam wybiera plan)
RESET plan_cache_mode;
DEALLOCATE ALL;
