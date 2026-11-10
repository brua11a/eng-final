GRADE_SCALE = (2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0)


def check_grade(value: float) -> float:
    """Pydantic validator body shared by teacher grades and opinion grades."""
    if value not in GRADE_SCALE:
        raise ValueError(f"grade must be one of {', '.join(map(str, GRADE_SCALE))}")
    return value
