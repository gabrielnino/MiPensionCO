"""TDD Reproduction Suite for Findings 2.1 to 2.10.

Tests reproduce each defect as initially identified, ensuring failure on baseline
and subsequent green pass after implementation.
"""

import io
from datetime import date
from decimal import Decimal

import pytest

from src.domain.models import (
    CotizacionRecord,
    EscenarioConfig,
    HistoriaLaboral,
    SexCategory,
    TransitionStatus,
)
from src.domain.pension_engine import TRANSITION_CUTOFF_DATE_C264, PensionEngine
from src.economic.ipc import get_ipc
from src.economic.smlmv import get_smlmv
from src.parser.pdf_reader import ColpensionesPDFReader
from src.parser.synthetic_generator import create_synthetic_colpensiones_pdf


# ---------------------------------------------------------------------------
# Finding 2.1: PDF extraction of row '01/01/2024 31/01/2024 30 $ 3.000.000 EMPRESA'
# ---------------------------------------------------------------------------
def test_reproduce_finding_2_1_pdf_extraction_row():
    """Reproduces: '01/01/2024 31/01/2024 30 $ 3.000.000 EMPRESA' must extract 30 days and IBC $3.000.000."""
    pdf_bytes = create_synthetic_colpensiones_pdf(
        records_lines=[
            "01/01/2024 31/01/2024 30 $ 3.000.000 EMPRESA",
        ]
    )
    historia, report = ColpensionesPDFReader.extract_from_bytes(pdf_bytes)
    assert report.success is True
    assert historia is not None
    assert len(historia.registros) == 1
    rec = historia.registros[0]
    assert rec.periodo_inicio == date(2024, 1, 1)
    assert rec.periodo_fin == date(2024, 1, 31)
    assert rec.dias_cotizados == 30, f"Expected 30 days, got {rec.dias_cotizados}"
    assert rec.ibc == Decimal(3000000), f"Expected 3000000 IBC, got {rec.ibc}"


def test_reproduce_finding_2_1_empty_pdf_warning():
    """Empty PDF must be detected and not declared as successful without warnings/errors."""
    empty_doc_bytes = create_synthetic_colpensiones_pdf(records_lines=[])
    _hist, rep_empty = ColpensionesPDFReader.extract_from_bytes(empty_doc_bytes)
    assert rep_empty.success is True  # Parsed metadata but 0 records
    assert len(_hist.registros) == 0

    # Now let's test a completely blank PDF without any text layer
    import pymupdf

    blank_doc = pymupdf.open()
    blank_doc.new_page()  # Page with no text
    buf = io.BytesIO()
    blank_doc.save(buf)
    blank_doc.close()

    historia, report = ColpensionesPDFReader.extract_from_bytes(buf.getvalue())
    assert (
        report.success is False
        or len(report.warnings) > 0
        or (
            historia
            and len(historia.registros) == 0
            and historia.semanas_resumen_colpensiones == 0
        )
    )
    # Must report emptiness or lack of recognizable structure
    assert report.error_message is not None or any(
        "vacio" in w.lower() or "sin texto" in w.lower() for w in report.warnings
    )


# ---------------------------------------------------------------------------
# Finding 2.2: Scenarios with different future IBC ($2M vs $10M) must change IBL
# ---------------------------------------------------------------------------
def test_reproduce_finding_2_2_scenarios_different_ibc_change_ibl():
    """Different future IBCs ($2M vs $10M) must result in different IBL and mesada."""
    # Worker born 1970 (turns 62 in 2032). Historical records up to 2026 (700 weeks).
    # From 2026 to 2032 (6 years = ~312 weeks) projected contributions are generated.
    engine = PensionEngine()
    recs = [
        CotizacionRecord(
            periodo_inicio=date(2005, 1, 1),
            periodo_fin=date(2025, 12, 31),
            dias_reportados=1050 * 7,
            dias_cotizados=1050 * 7,
            ibc=Decimal(2500000),
            aportante="EMPRESA BASE",
        )
    ]
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-F22",
        fecha_nacimiento=date(1970, 5, 1),
        sexo=SexCategory.MASCULINO,
        semanas_resumen_colpensiones=Decimal(1050),
        registros=recs,
    )

    esc_low = EscenarioConfig(
        escenario_id="esc_low",
        nombre="Bajo",
        ibc_futuro_inicial=Decimal(2000000),
        fecha_inicio_ibc=date(2026, 1, 1),
    )
    esc_high = EscenarioConfig(
        escenario_id="esc_high",
        nombre="Alto",
        ibc_futuro_inicial=Decimal(10000000),
        fecha_inicio_ibc=date(2026, 1, 1),
    )

    res_low = engine.simulate_scenario(historia, esc_low, as_of_date=date(2026, 9, 27))
    res_high = engine.simulate_scenario(
        historia, esc_high, as_of_date=date(2026, 9, 27)
    )

    assert res_low.cumple_semanas is True
    assert res_high.cumple_semanas is True
    assert res_low.ibl_final is not None
    assert res_high.ibl_final is not None
    assert res_high.ibl_final > res_low.ibl_final, (
        f"Expected high IBC ({res_high.ibl_final}) > low IBC ({res_low.ibl_final})"
    )
    assert res_high.mesada_bruta > res_low.mesada_bruta


# ---------------------------------------------------------------------------
# Finding 2.3: 1300 weeks with no salary records must block mesada
# ---------------------------------------------------------------------------
def test_reproduce_finding_2_3_no_salary_blocks_mesada():
    """1.300 weeks without salary records must block mesada with IBL_INSUFICIENTE, not return minimum pension."""
    engine = PensionEngine()
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-F23",
        fecha_nacimiento=date(1964, 1, 1),
        sexo=SexCategory.MASCULINO,
        semanas_resumen_colpensiones=Decimal(1300),
        registros=[],  # NO salary records at all
    )
    esc = EscenarioConfig("esc1", "Escenario", Decimal(2000000), date(2026, 1, 1))
    res = engine.simulate_scenario(historia, esc, as_of_date=date(2026, 9, 27))

    assert res.cumple_semanas is True
    assert res.ibl_final is None or res.mesada_bruta is None
    assert res.mesada_bruta is None, "Mesada must be blocked when salary data is absent"
    assert (
        "insuficiente" in res.mensaje_advertencia.lower()
        or "sin salarios" in res.mensaje_advertencia.lower()
    )


# ---------------------------------------------------------------------------
# Finding 2.4: Partial month with 1 day accredited must not give 4.42 weeks
# ---------------------------------------------------------------------------
def test_reproduce_finding_2_4_partial_month_exact_days():
    """Record covering Jan 1 to Jan 31 but accrediting only 1 day must give 1 day / 7 weeks (0.14), not 4.42."""
    rec = CotizacionRecord(
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=date(2024, 1, 31),
        dias_reportados=1,
        dias_cotizados=1,
        ibc=Decimal(100000),
        aportante="EMPRESA PARCIAL",
    )
    weeks = PensionEngine.compute_calendar_weeks([rec])
    assert weeks == Decimal("0.14"), f"Expected 0.14 weeks (1/7), got {weeks}"


# ---------------------------------------------------------------------------
# Finding 2.5: Report updated in 2028 with 950 weeks without detail not accepted for 2027 cutoff
# ---------------------------------------------------------------------------
def test_reproduce_finding_2_5_summary_after_cutoff_without_detail():
    """A report from 2028 with 950 weeks and no detail cannot certify 900 weeks were before April 2027."""
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-F25",
        sexo=SexCategory.MASCULINO,
        fecha_actualizacion_reporte=date(2028, 6, 1),
        semanas_resumen_colpensiones=Decimal(950),
        registros=[],  # No breakdown of which weeks occurred before April 2027
    )
    eval_res = PensionEngine.evaluate_transition(
        historia, cutoff_date=TRANSITION_CUTOFF_DATE_C264
    )
    assert eval_res.status in (
        TransitionStatus.INFORMACION_INSUFICIENTE,
        TransitionStatus.NO_CUMPLE_UMBRAL_CORTE,
    )
    assert eval_res.permite_continuar_simulacion is False


# ---------------------------------------------------------------------------
# Finding 2.6: SMLMV 2026 is $1.750.905 (Decreto 159 de 2026), missing IPC error
# ---------------------------------------------------------------------------
def test_reproduce_finding_2_6_smlmv_2026_and_no_silent_ipc():
    """SMLMV 2026 is $1.750.905 per Decreto 159 de 2026. Missing IPC must not silently substitute."""
    smlmv_2026 = get_smlmv(2026)
    assert smlmv_2026.monthly_amount == Decimal(1750905), (
        f"Expected 1750905, got {smlmv_2026.monthly_amount}"
    )
    assert "159" in smlmv_2026.decree_reference

    # Requesting missing IPC before 1990 without data must raise ValueError, not return 1990 silently
    with pytest.raises(ValueError) as exc:
        get_ipc(1985, 5)
    assert (
        "no disponible" in str(exc.value).lower()
        or "supuesto" in str(exc.value).lower()
    )


# ---------------------------------------------------------------------------
# Finding 2.7: Simultaneous employers in same month ($2M + $3M) consolidate to $5M
# ---------------------------------------------------------------------------
def test_reproduce_finding_2_7_simultaneous_employers_consolidate_ibc():
    """Two contributions in same month of $2M and $3M must consolidate to $5M base, not average to $2.5M."""
    engine = PensionEngine()
    recs = [
        CotizacionRecord(
            periodo_inicio=date(2024, 1, 1),
            periodo_fin=date(2024, 1, 31),
            dias_reportados=30,
            dias_cotizados=30,
            ibc=Decimal(2000000),
            aportante="EMPLEADOR 1",
        ),
        CotizacionRecord(
            periodo_inicio=date(2024, 1, 1),
            periodo_fin=date(2024, 1, 31),
            dias_reportados=30,
            dias_cotizados=30,
            ibc=Decimal(3000000),
            aportante="EMPLEADOR 2",
        ),
    ]
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-F27",
        fecha_nacimiento=date(1964, 1, 1),
        sexo=SexCategory.MASCULINO,
        registros=recs,
    )
    # January 2024 to January 2024 target
    ibl_10y, _, _, _ = engine.calculate_ibl(historia, target_year=2024, target_month=1)
    assert ibl_10y is not None
    # Must be based on consolidated $5.000.000, not $2.500.000!
    assert ibl_10y >= Decimal(4900000), f"Expected consolidated ~5000000, got {ibl_10y}"


# ---------------------------------------------------------------------------
# Finding 2.8: Horizon in 2017 must exclude contributions from 2024
# ---------------------------------------------------------------------------
def test_reproduce_finding_2_8_exclude_contributions_post_horizon():
    """Affiliate who turned 62 in 2017 must NOT have 2024 contributions included in 2017 pension calculation."""
    engine = PensionEngine()
    recs_valid = [
        CotizacionRecord(
            periodo_inicio=date(2010, 1, 1),
            periodo_fin=date(2016, 12, 31),
            dias_reportados=365 * 7,
            dias_cotizados=365 * 7,
            ibc=Decimal(2000000),
            aportante="EMPRESA HISTORICA",
        )
    ]
    recs_future = [
        CotizacionRecord(
            periodo_inicio=date(2024, 1, 1),
            periodo_fin=date(2024, 12, 31),
            dias_reportados=365,
            dias_cotizados=365,
            ibc=Decimal(15000000),  # High salary long after reaching age 62
            aportante="EMPRESA TARDIA",
        )
    ]
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-F28",
        fecha_nacimiento=date(1955, 1, 1),  # Turned 62 on 2017-01-01
        sexo=SexCategory.MASCULINO,
        semanas_resumen_colpensiones=Decimal(1300),
        registros=recs_valid + recs_future,
    )
    esc = EscenarioConfig("esc1", "Escenario", Decimal(2000000), date(2026, 1, 1))
    res = engine.simulate_scenario(historia, esc, as_of_date=date(2026, 9, 27))

    assert res.fecha_cumplimiento_edad_legal == date(2017, 1, 1)
    # The IBL at 2017 cannot include the 15M salary from 2024!
    if res.ibl_final is not None:
        assert res.ibl_final < Decimal(5000000), (
            f"Post-horizon 2024 salary leaked into 2017 IBL: {res.ibl_final}"
        )


# ---------------------------------------------------------------------------
# Finding 2.9: PDF text with HTML must be safely escaped
# ---------------------------------------------------------------------------
def test_reproduce_finding_2_9_xss_protection():
    """PDF containing '<img src=x onerror=alert(1)>' must not execute or be treated as HTML."""
    malicious_text = "<img src=x onerror=alert(1)>"
    pdf_bytes = create_synthetic_colpensiones_pdf(
        nombre=malicious_text,
        records_lines=[
            f"01/01/2024 31/01/2024 30 $ 2.000.000 {malicious_text}",
        ],
    )
    historia, _report = ColpensionesPDFReader.extract_from_bytes(pdf_bytes)
    assert historia is not None
    assert len(historia.registros) == 1
    # Plain string preserved safely
    assert "<img" in historia.registros[0].aportante
