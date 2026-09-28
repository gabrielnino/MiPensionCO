"""Pure selection of future contribution days; never changes historical records."""

from datetime import date, timedelta


def contribution_dates(
    start: date,
    end: date,
    target_days: int | None,
    alternating: bool,
    latest: bool,
    pauses: list[tuple[date, date]],
) -> list[date]:
    """Select dates before retirement, alternating anniversary years if requested.

    Latest selects the last eligible days; combining both options preserves the
    alternating cycle anchored at start. Insufficient available days remain a deficit.
    """
    eligible: list[date] = []
    current = start
    while current < end:
        anniversary_year = (
            current.year
            - start.year
            - ((current.month, current.day) < (start.month, start.day))
        )
        if (not alternating or anniversary_year % 2 == 0) and not any(
            a <= current <= b for a, b in pauses
        ):
            eligible.append(current)
        current += timedelta(days=1)
    if target_days is None:
        return eligible
    if target_days <= 0:
        return []
    return eligible[-target_days:] if latest else eligible[:target_days]
