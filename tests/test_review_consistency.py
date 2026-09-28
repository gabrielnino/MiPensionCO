"""Review, exclusion and reconciliation regression tests."""

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from src.api.app import app, domain_to_dto
from src.domain.models import (
    CotizacionRecord,
    HistoriaLaboral,
    ProvenanceType,
    SexCategory,
)
from src.domain.pension_engine import PensionEngine
from src.domain.validation import reconcile_labor_history


def history() -> HistoriaLaboral:
    record = CotizacionRecord(
        date(2024, 1, 1), date(2024, 1, 31), 31, 31, Decimal(3000000), "SYNTHETIC"
    )
    return HistoriaLaboral(
        "SYNTHETIC",
        sexo=SexCategory.MASCULINO,
        semanas_resumen_colpensiones=Decimal("4.42"),
        registros=[record],
    )


def test_review_uses_calendar_union() -> None:
    h = history()
    h.registros.append(replace(h.registros[0], aportante="OTHER"))
    result = reconcile_labor_history(h)
    assert result["semanas_totales_activas"] == Decimal("4.42")
    assert result["semanas_totales_activas"] == PensionEngine.compute_calendar_weeks(
        h.registros
    )
    assert result["permite_continuar"]


def test_excluded_record_cannot_establish_transition_even_with_summary() -> None:
    h = history()
    h.registros = [
        replace(
            h.registros[0],
            periodo_inicio=date(2003, 1, 1),
            periodo_fin=date(2003, 1, 1) + timedelta(days=6299),
            dias_cotizados=6300,
            dias_reportados=6300,
            excluido_del_calculo=True,
        )
    ]
    for summary in [Decimal(0), Decimal(900)]:
        h.semanas_resumen_colpensiones = summary
        result = PensionEngine.evaluate_transition(h)
        assert not result.permite_continuar_simulacion
        assert result.semanas_acreditadas_al_corte == 0
    assert h.registros[0].excluido_del_calculo


def test_discrepancy_blocks_review_and_save_revision() -> None:
    h = history()
    h.semanas_resumen_colpensiones = Decimal(900)
    result = reconcile_labor_history(h)
    assert result["tiene_discrepancia"]
    assert not result["permite_continuar"]
    response = TestClient(app).post(
        "/api/review/save-revision", json={"historia": domain_to_dto(h).model_dump()}
    )
    assert response.status_code == 400
    assert not response.json()["success"]


def test_correcting_income_does_not_remove_time_from_reconciliation() -> None:
    h = history()
    h.registros = [
        replace(
            h.registros[0],
            origen=ProvenanceType.CORRECCION_MANUAL,
            ibc=Decimal(4000000),
        )
    ]
    result = reconcile_labor_history(h)
    assert result["semanas_recalculadas_detalle"] == Decimal("4.42")
    assert not result["tiene_discrepancia"]
    assert result["permite_continuar"]


def test_subweek_difference_crossing_transition_threshold_is_blocked() -> None:
    h = history()
    start = date(2003, 1, 1)
    h.registros = [
        replace(
            h.registros[0],
            periodo_inicio=start,
            periodo_fin=start + timedelta(days=6298),
            dias_cotizados=6299,
            dias_reportados=6299,
        )
    ]
    h.semanas_resumen_colpensiones = Decimal(900)
    result = reconcile_labor_history(h)
    assert result["tiene_discrepancia"]
    assert not result["permite_continuar"]
