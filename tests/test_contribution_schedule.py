from datetime import date

from src.domain.contribution_schedule import contribution_dates


def test_alternating_anniversary_years() -> None:
    dates = contribution_dates(
        date(2026, 9, 28), date(2029, 9, 28), None, True, False, []
    )
    assert date(2027, 9, 27) in dates
    assert date(2027, 9, 28) not in dates
    assert date(2028, 9, 28) in dates


def test_latest_days_preserve_pauses_and_target() -> None:
    dates = contribution_dates(
        date(2030, 1, 1),
        date(2030, 2, 1),
        3,
        False,
        True,
        [(date(2030, 1, 30), date(2030, 1, 30))],
    )
    assert dates == [date(2030, 1, 28), date(2030, 1, 29), date(2030, 1, 31)]
    assert (
        contribution_dates(date(2030, 1, 1), date(2030, 2, 1), 0, True, True, []) == []
    )


def test_insufficient_time_does_not_invent_days() -> None:
    assert (
        len(contribution_dates(date(2030, 1, 1), date(2030, 1, 4), 20, False, True, []))
        == 3
    )
