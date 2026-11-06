_SEASON_ORDER = {"Z": 0, "winter": 0, "L": 1, "summer": 1}


def cycle_sort_key(year: str, season: str) -> tuple:
    return (year, _SEASON_ORDER.get(season, 2), season)
