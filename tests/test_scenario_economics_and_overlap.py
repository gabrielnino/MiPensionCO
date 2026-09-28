"""Regressions for scenario assumptions and documentary/declaration overlap."""

from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from src.domain.models import (
    CotizacionRecord,
    EscenarioConfig,
    HistoriaLaboral,
    ProvenanceType,
    SexCategory,
)
from src.domain.pension_engine import PensionEngine
from src.economic.ipc import calculate_ipc_adjustment_factor


def history() -> HistoriaLaboral:
    return HistoriaLaboral(
        cedula_enmascarada="SYNTHETIC",
        fecha_nacimiento=date(1965, 1, 1),
        sexo=SexCategory.MASCULINO,
        semanas_resumen_colpensiones=Decimal("4.42"),
        registros=[
            CotizacionRecord(
                date(2024, 1, 1),
                date(2024, 1, 31),
                31,
                31,
                Decimal(3000000),
                "SYNTHETIC",
            )
        ],
    )


def scenario() -> EscenarioConfig:
    return EscenarioConfig("test", "Synthetic", Decimal(3000000), date(2027, 1, 1))


def test_scenario_growth_is_applied_without_cross_scenario_state() -> None:
    engine = PensionEngine()
    for growth, expected in [("0", "1750905"), ("0.20", "2101086"), ("0", "1750905")]:
        result = engine.simulate_scenario(
            history(),
            replace(scenario(), supuesto_crecimiento_smlmv=Decimal(growth)),
            as_of_date=date(2026, 9, 27),
        )
        assert result.smlmv_referencia_retiro == Decimal(expected)
    assert engine.projector.assumptions.assumed_annual_smlmv_growth == Decimal("0.055")


@pytest.mark.parametrize(
    "start,end,days,additional",
    [
        (date(2024, 1, 1), date(2024, 1, 31), 31, "0.00"),
        (date(2024, 1, 25), date(2024, 2, 7), 14, "1.00"),
        (date(2024, 2, 1), date(2024, 2, 7), 7, "1.00"),
    ],
)
def test_declared_days_only_add_uncovered_time(
    start: date,
    end: date,
    days: int,
    additional: str,
) -> None:
    original = history()
    engine = PensionEngine()
    before = engine.simulate_scenario(original, scenario())
    declared = replace(
        original.registros[0],
        periodo_inicio=start,
        periodo_fin=end,
        dias_cotizados=days,
        dias_reportados=days,
        origen=ProvenanceType.DECLARACION_USUARIO,
    )
    revised = replace(original, registros=[*original.registros, declared])
    after = engine.simulate_scenario(revised, scenario())
    assert (
        after.semanas_totales_a_la_edad - before.semanas_totales_a_la_edad
        == Decimal(additional)
    )
    if start <= date(2024, 1, 31):
        assert "superpos" in after.mensaje_advertencia.lower()
        assert after.mesada_bruta is None
    assert len(original.registros) == 1


def test_overlap_blocks_pension_even_when_weeks_are_sufficient() -> None:
    start, end = date(2003, 1, 1), date(2026, 8, 31)
    days = (end - start).days + 1
    record = CotizacionRecord(start, end, days, days, Decimal(3000000), "SYNTHETIC")
    original = replace(
        history(),
        sexo=SexCategory.FEMENINO,
        fecha_nacimiento=date(1970, 1, 1),
        semanas_resumen_colpensiones=Decimal(0),
        registros=[record],
    )
    engine = PensionEngine()
    baseline = engine.simulate_scenario(original, scenario())
    assert baseline.mesada_bruta is not None
    revised = replace(
        original,
        registros=[record, replace(record, origen=ProvenanceType.DECLARACION_USUARIO)],
    )
    result = engine.simulate_scenario(revised, scenario())
    assert result.semanas_totales_a_la_edad == baseline.semanas_totales_a_la_edad
    assert result.mesada_bruta is None
    assert result.limite_aplicado == "BLOQUEADO_POR_SUPERPOSICION"


def test_real_valuation_uses_same_inflation_as_scenario() -> None:
    start, end = date(2003, 1, 1), date(2026, 8, 31)
    days = (end - start).days + 1
    original = replace(
        history(),
        sexo=SexCategory.FEMENINO,
        fecha_nacimiento=date(1970, 1, 1),
        semanas_resumen_colpensiones=Decimal(0),
        registros=[
            CotizacionRecord(start, end, days, days, Decimal(3000000), "SYNTHETIC")
        ],
    )
    configured = replace(scenario(), supuesto_inflacion=Decimal("0.20"))
    result = PensionEngine().simulate_scenario(original, configured)
    assert result.valor_despues_descuentos is not None
    factor = calculate_ipc_adjustment_factor(2026, 8, 2027, 1, Decimal("0.20"))
    assert result.valor_real_poder_adquisitivo == (
        result.valor_despues_descuentos / factor
    ).quantize(Decimal(1))
