from collections import defaultdict
from typing import Iterable, Mapping

from app.graph_backend.cycles import cycle_sort_key


def average_grade(rows: Iterable[Mapping]) -> float | None:
    """ECTS-weighted average over subjects, using each subject's latest complete attempt.

    Each row is one group type of a subject in a cycle the student attended, with keys
    subject, ects, year, season, type, weight and grade (None when not graded yet).
    An attempt counts only when every group type has a grade; a type graded in several
    groups of the same attempt uses their mean.
    """
    grades: dict[tuple, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    weights: dict[tuple, dict[str, float]] = defaultdict(dict)
    ects: dict[str, int | None] = {}
    for row in rows:
        attempt = (row["subject"], row["year"], row["season"])
        grades[attempt][row["type"]].append(row["grade"])
        weights[attempt][row["type"]] = row["weight"]
        ects[row["subject"]] = row["ects"]

    latest: dict[str, tuple[tuple, float]] = {}
    for attempt, by_type in grades.items():
        if any(g is None for values in by_type.values() for g in values):
            continue
        total_weight = sum(weights[attempt].values())
        if not total_weight:
            continue
        grade = sum(
            weights[attempt][t] * sum(values) / len(values) for t, values in by_type.items()
        ) / total_weight
        subject, year, season = attempt
        order = cycle_sort_key(year, season)
        if subject not in latest or order > latest[subject][0]:
            latest[subject] = (order, grade)

    weighted = [(grade, ects[s]) for s, (_, grade) in latest.items() if ects[s]]
    ects_total = sum(e for _, e in weighted)
    if not ects_total:
        return None
    return sum(grade * e for grade, e in weighted) / ects_total
