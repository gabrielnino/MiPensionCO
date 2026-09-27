from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

from src.domain.models import (
    CotizacionRecord,
    EscenarioConfig,
    HistoriaLaboral,
    SexCategory,
)
from src.domain.pension_engine import PensionEngine


def test_stop_at_minimum_and_continue_are_independent() -> None:
    end = date(2026, 9, 27)
    record = CotizacionRecord(
        end - timedelta(days=9092), end, 9093, 9093, Decimal(3000000), "TEST"
    )
    history = HistoriaLaboral(
        "TEST",
        fecha_nacimiento=date(1981, 3, 26),
        sexo=SexCategory.MASCULINO,
        registros=[record],
        semanas_resumen_colpensiones=Decimal(1299),
    )
    scenario = EscenarioConfig(
        "test", "Test", Decimal(3000000), date(2026, 9, 28), aportar_hasta_minimo=True
    )
    engine = PensionEngine()
    limited = engine.simulate_scenario(history, scenario, as_of_date=end)
    continued = engine.simulate_scenario(
        history, replace(scenario, aportar_hasta_minimo=False), as_of_date=end
    )
    assert limited.semanas_totales_a_la_edad == Decimal(1300)
    assert limited.semanas_futuras_proyectadas == Decimal(1)
    assert continued.semanas_totales_a_la_edad > limited.semanas_totales_a_la_edad
    assert (
        limited.fecha_cumplimiento_edad_legal == continued.fecha_cumplimiento_edad_legal
    )

    already_met = replace(history, semanas_resumen_colpensiones=Decimal(1300))
    assert (
        engine.simulate_scenario(
            already_met, scenario, as_of_date=end
        ).semanas_futuras_proyectadas
        == 0
    )
    paused = replace(
        scenario, periodos_sin_aporte=[(date(2026, 9, 28), date(2026, 10, 10))]
    )
    assert (
        engine.simulate_scenario(
            history, paused, as_of_date=end
        ).semanas_futuras_proyectadas
        == 1
    )
