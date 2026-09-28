from dataclasses import replace
from datetime import date
from decimal import Decimal

from src.domain.models import CotizacionRecord
from src.domain.pension_engine import PensionEngine


def test_documentary_month_preserves_days_and_combines_employers() -> None:
    a = CotizacionRecord(
        date(2008, 2, 1),
        date(2008, 2, 29),
        27,
        27,
        Decimal(100000),
        "A",
        periodo_mensual_reportado=True,
    )
    b = replace(a, aportante="B", dias_cotizados=3)
    assert PensionEngine.compute_calendar_weeks([a, b]) == Decimal("4.29")
    july = replace(
        a,
        periodo_inicio=date(2009, 7, 1),
        periodo_fin=date(2009, 7, 31),
        dias_cotizados=18,
    )
    assert PensionEngine.compute_calendar_weeks(
        [july, replace(july, aportante="B", dias_cotizados=10)]
    ) == Decimal("4.00")
    assert PensionEngine.compute_calendar_weeks(
        [replace(a, dias_cotizados=30)]
    ) == Decimal("4.29")
    assert PensionEngine.compute_calendar_weeks([a, a, b]) == Decimal("4.29")
    assert PensionEngine.compute_calendar_weeks(
        [a, replace(b, excluido_del_calculo=True)]
    ) == Decimal("3.86")
