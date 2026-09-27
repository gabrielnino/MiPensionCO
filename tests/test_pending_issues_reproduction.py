"""TDD Reproduction Suite for Pending Issues (A through I).

Verifies reproduction of the issues identified in the specification:
A. Complete PDF extraction audit without truncation
B. Elimination of sensitive information from technical logs
C. Exact partial pauses calculation (days subtraction, unions, income weighting)
D. No projection of future contributions on unknown past
E. Separation of calendar coverage vs billing conventions
F. Exclusion of post-horizon contributions across all calculations (including straddling)
G. No automatic selection of max(semanas_doc, semanas_cal)
H. Explicit modeling of missing days in PDF (no invention of 31 days)
I. Elimination of silent IPC substitutions
"""

from datetime import date
from decimal import Decimal

import pytest

from src.audit.service import TECH_LOG_FILE, AuditService
from src.domain.models import (
    CotizacionRecord,
    EscenarioConfig,
    HistoriaLaboral,
    SexCategory,
)
from src.domain.pension_engine import PensionEngine
from src.economic.ipc import get_ipc
from src.parser.pdf_reader import ColpensionesPDFReader
from src.parser.synthetic_generator import create_synthetic_colpensiones_pdf


# ---------------------------------------------------------------------------
# Test A: Full PDF extraction audit (raw text, fragments, no truncation)
# ---------------------------------------------------------------------------
def test_reproduce_issue_a_full_extraction_audit():
    """Extraction audit must store full raw page text, all fragments with stable IDs, and not truncate uninterpreted lines."""
    pdf_bytes = create_synthetic_colpensiones_pdf(
        records_lines=[
            "01/01/2024 31/01/2024 30 $ 3.000.000 EMPRESA A",
            "LINEA_NO_INTERPRETADA_1",
            "LINEA_NO_INTERPRETADA_2",
            "LINEA_NO_INTERPRETADA_3",
            "LINEA_NO_INTERPRETADA_4",
            "LINEA_NO_INTERPRETADA_5",
            "LINEA_NO_INTERPRETADA_6",
            "LINEA_NO_INTERPRETADA_7",
            "LINEA_NO_INTERPRETADA_8",
            "LINEA_NO_INTERPRETADA_9",
            "LINEA_NO_INTERPRETADA_10",
            "LINEA_NO_INTERPRETADA_11",  # 11th line previously truncated by [:10]
        ]
    )
    exec_id = "test-exec-audit-a"
    _historia, report = ColpensionesPDFReader.extract_from_bytes(
        pdf_bytes, execution_id=exec_id
    )
    assert report.success is True
    audit = AuditService.get_or_create_audit(exec_id)

    assert len(audit.pages_audit) >= 1
    p1 = audit.pages_audit[0]

    # Must contain full raw text of the page
    assert hasattr(p1, "raw_page_text") and len(p1.raw_page_text) > 0, (
        "Page extraction audit does not store raw_page_text!"
    )

    # Must contain all fragments detected with stable IDs and status
    assert hasattr(p1, "fragments") and len(p1.fragments) > 0, (
        "Page extraction audit does not store individual fragments!"
    )

    # Line 11 must NOT be silently truncated
    assert hasattr(p1, "uninterpreted_lines")
    # All 11 uninterpreted lines must be preserved without silent truncation
    assert (
        len(p1.uninterpreted_lines) >= 11 or audit.extraction_status == "INCOMPLETA"
    ), f"Uninterpreted lines were silently truncated to {len(p1.uninterpreted_lines)}!"


# ---------------------------------------------------------------------------
# Test B: Eliminate sensitive info from technical logs
# ---------------------------------------------------------------------------
def test_reproduce_issue_b_technical_log_privacy():
    """Technical log must NOT contain affiliate name, employer name, salary numbers, or calculated mesada."""
    secret_name = "JUAN_PEREZ_CONFIDENCIAL"
    secret_employer = "EMPRESA_SECRETA_XYZ"
    secret_salary = Decimal(12345678)

    recs = [
        CotizacionRecord(
            periodo_inicio=date(2020, 1, 1),
            periodo_fin=date(2024, 12, 31),
            dias_reportados=365 * 5,
            dias_cotizados=365 * 5,
            ibc=secret_salary,
            aportante=secret_employer,
        )
    ]
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-TEST-B",
        nombre_enmascarado=secret_name,
        fecha_nacimiento=date(1964, 1, 1),
        sexo=SexCategory.MASCULINO,
        semanas_resumen_colpensiones=Decimal(1350),
        registros=recs,
    )

    engine = PensionEngine()
    esc = EscenarioConfig(
        "esc_secret", "Escenario Privado", Decimal(5000000), date(2026, 1, 1)
    )

    import uuid

    unique_run_id = f"test-priv-{uuid.uuid4().hex[:8]}"
    exec_id = unique_run_id

    # Run simulation
    res = engine.simulate_scenario(
        historia, esc, as_of_date=date(2026, 9, 27), execution_id=exec_id
    )

    # Read technical log file
    assert TECH_LOG_FILE.exists()
    with open(TECH_LOG_FILE, "r", encoding="utf-8") as f:
        log_content = f.read()

    # Search for execution entries
    exec_lines = [line for line in log_content.splitlines() if unique_run_id in line]
    assert len(exec_lines) > 0, (
        "No technical log entry was generated for this execution"
    )

    for line in exec_lines:
        assert secret_name not in line, f"Secret name leaked in technical log: {line}"
        assert secret_employer not in line, (
            f"Secret employer leaked in technical log: {line}"
        )
        assert "12345678" not in line, f"Secret salary leaked in technical log: {line}"
        assert "Escenario Privado" not in line, (
            f"Scenario name leaked in technical log: {line}"
        )
        if res.mesada_bruta:
            mesada_str = f"{res.mesada_bruta:,.0f}"
            assert mesada_str not in line, (
                f"Mesada amount leaked in technical log: {line}"
            )


# ---------------------------------------------------------------------------
# Test C: Correct partial pauses (1 day, start, end, across 2 months, union, suspended, outside)
# ---------------------------------------------------------------------------
def test_reproduce_issue_c_partial_pauses_cases():
    """A 1-day pause within October 2026 must deduct only 1 day, keeping 30 calendar days (not dropping the month)."""
    engine = PensionEngine()
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-TEST-C",
        fecha_nacimiento=date(1966, 11, 1),  # Reaches 62 on 2028-11-01
        sexo=SexCategory.MASCULINO,
        semanas_resumen_colpensiones=Decimal(1200),
        registros=[
            CotizacionRecord(
                periodo_inicio=date(2020, 1, 1),
                periodo_fin=date(2026, 9, 26),
                dias_reportados=2400,
                dias_cotizados=2400,
                ibc=Decimal(3000000),
                aportante="EMPRESA BASE",
            )
        ],
    )

    # Case 1: 1-day pause in October 2026 (2026-10-15 to 2026-10-15)
    esc_1day = EscenarioConfig(
        escenario_id="esc_1day",
        nombre="Pausa 1 dia",
        ibc_futuro_inicial=Decimal(3000000),
        fecha_inicio_ibc=date(2026, 10, 1),
        periodos_sin_aporte=[(date(2026, 10, 15), date(2026, 10, 15))],
    )
    res_1day = engine.simulate_scenario(
        historia, esc_1day, as_of_date=date(2026, 9, 27), execution_id="exec-pause-1"
    )
    audit_1 = AuditService.get_or_create_audit("exec-pause-1")
    _sc_audit_1 = audit_1.scenarios_audit[-1]

    # In October 2026, there are 31 calendar days. Deducting 1 day leaves 30 calendar days.
    # Currently, the month is completely dropped (0 days)!
    # Find October record in projected records:
    # If the month was dropped, future weeks will be reduced by an entire month (~4.28 weeks) instead of ~0.14 weeks (1 day)!
    # Let's verify that October was NOT dropped:
    esc_no_pause = EscenarioConfig(
        escenario_id="esc_no_pause",
        nombre="Sin Pausa",
        ibc_futuro_inicial=Decimal(3000000),
        fecha_inicio_ibc=date(2026, 10, 1),
        periodos_sin_aporte=[],
    )
    res_no_pause = engine.simulate_scenario(
        historia, esc_no_pause, as_of_date=date(2026, 9, 27)
    )

    diff_weeks = (
        res_no_pause.semanas_futuras_proyectadas - res_1day.semanas_futuras_proyectadas
    )
    # Diff should be exactly 1 day / 7 = ~0.14 weeks, NOT ~4.28 weeks!
    assert diff_weeks <= Decimal("0.20"), (
        f"A 1-day pause caused a reduction of {diff_weeks} weeks! The entire month was eliminated!"
    )


# ---------------------------------------------------------------------------
# Test D: Do not project contributions on unknown past
# ---------------------------------------------------------------------------
def test_reproduce_issue_d_no_projection_on_unknown_past():
    """Future projection from evaluation date (2026-09-27) to horizon (2027-02-01) must NOT generate 55 weeks."""
    engine = PensionEngine()
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-TEST-D",
        fecha_nacimiento=date(1965, 2, 1),  # Reaches 62 on 2027-02-01
        sexo=SexCategory.MASCULINO,
        semanas_resumen_colpensiones=Decimal(1250),
        registros=[
            CotizacionRecord(
                periodo_inicio=date(2020, 1, 1),
                periodo_fin=date(2025, 12, 31),  # Last contribution is Dec 2025
                dias_reportados=2190,
                dias_cotizados=2190,
                ibc=Decimal(3000000),
                aportante="EMPRESA HISTORICA",
            )
        ],
    )
    # Scenario starts in Jan 2026, but evaluation is Sept 27, 2026
    esc = EscenarioConfig(
        escenario_id="esc_past",
        nombre="Escenario Pasado",
        ibc_futuro_inicial=Decimal(3000000),
        fecha_inicio_ibc=date(2026, 1, 1),
    )

    # Evaluating on 2026-09-27
    res = engine.simulate_scenario(historia, esc, as_of_date=date(2026, 9, 27))
    # Between 2026-09-27 and 2027-02-01 there are 127 calendar days = 18.14 weeks.
    # It must NOT project 55.42 weeks by filling the unknown past (Jan 2026 to Sept 2026)!
    assert res.semanas_futuras_proyectadas <= Decimal("19.00"), (
        f"Engine projected {res.semanas_futuras_proyectadas} future weeks, filling the unknown past!"
    )


# ---------------------------------------------------------------------------
# Test E: Separate calendar days for weeks vs billing conventions
# ---------------------------------------------------------------------------
def test_reproduce_issue_e_calendar_vs_billing_conventions():
    """Full January (31 calendar days) must give 31/7 weeks (4.4285), not be capped at 30 days (4.2857)."""
    # In pension_engine.py line 624:
    # month_days = min(30, span_days)
    # total_proj_days = sum(r.dias_cotizados for r in projected_future_records)
    # semanas_proyectadas = Decimal(total_proj_days) / Decimal(7)
    # This was clamping calendar coverage to 30 days!
    engine = PensionEngine()
    # We test projection for 1 full month of January 2027:
    # Calendar coverage: 31 days -> 31/7 = 4.43 weeks
    # If clamped to 30 days -> 30/7 = 4.28 weeks
    # Also test February 2028 (leap year, 29 days) -> 29 days.
    # The engine must separate calendar days of coverage for weeks from 30-day billing convention!
    # Scenario for January 2027 only (evaluation 2026-12-31, horizon 2027-02-01)
    esc_jan = EscenarioConfig(
        escenario_id="esc_jan",
        nombre="Enero Completo",
        ibc_futuro_inicial=Decimal(3000000),
        fecha_inicio_ibc=date(2027, 1, 1),
    )
    # Affiliate turns 62 on 2027-02-01
    historia_jan = HistoriaLaboral(
        cedula_enmascarada="ANON-TEST-E",
        fecha_nacimiento=date(1965, 2, 1),  # 62 on 2027-02-01
        sexo=SexCategory.MASCULINO,
        semanas_resumen_colpensiones=Decimal(1200),
        registros=[
            CotizacionRecord(
                periodo_inicio=date(2020, 1, 1),
                periodo_fin=date(2026, 12, 31),
                dias_reportados=2550,
                dias_cotizados=2550,
                ibc=Decimal(3000000),
                aportante="EMPRESA E",
            )
        ],
    )
    res_jan = engine.simulate_scenario(
        historia_jan, esc_jan, as_of_date=date(2026, 12, 31)
    )
    # January 2027 has 31 calendar days.
    # Calendar weeks must be 31 / 7 = 4.4285... = 4.42 (or 4.43) weeks.
    # Currently min(30, 31) gives 30 / 7 = 4.28 weeks!
    assert res_jan.semanas_futuras_proyectadas >= Decimal("4.42"), (
        f"January 2027 (31 calendar days) was clamped to 30 days giving only {res_jan.semanas_futuras_proyectadas} weeks!"
    )


# ---------------------------------------------------------------------------
# Test F: Exclude post-horizon contributions in ALL calculations (including straddling)
# ---------------------------------------------------------------------------
def test_reproduce_issue_f_exclude_post_horizon_weeks_and_straddle():
    """Record straddling the retirement horizon must be prorated, and post-horizon weeks excluded from calendar count."""
    engine = PensionEngine()
    # Affiliate turned 62 on 2020-05-15
    recs = [
        CotizacionRecord(
            periodo_inicio=date(2018, 1, 1),
            periodo_fin=date(2020, 4, 30),
            dias_reportados=850,
            dias_cotizados=850,
            ibc=Decimal(2000000),
            aportante="EMP 1",
        ),
        # Straddles horizon (2020-05-01 to 2020-05-31). Only days up to 2020-05-15 (15 days) should count!
        CotizacionRecord(
            periodo_inicio=date(2020, 5, 1),
            periodo_fin=date(2020, 5, 31),
            dias_reportados=31,
            dias_cotizados=31,
            ibc=Decimal(2000000),
            aportante="EMP 1",
        ),
        # Fully after horizon
        CotizacionRecord(
            periodo_inicio=date(2020, 6, 1),
            periodo_fin=date(2022, 12, 31),
            dias_reportados=940,
            dias_cotizados=940,
            ibc=Decimal(10000000),
            aportante="EMP 2",
        ),
    ]
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-TEST-F",
        fecha_nacimiento=date(1958, 5, 15),  # 62 on 2020-05-15
        sexo=SexCategory.MASCULINO,
        semanas_resumen_colpensiones=Decimal(1300),
        registros=recs,
    )
    esc = EscenarioConfig("esc1", "Escenario", Decimal(2000000), date(2026, 1, 1))
    res = engine.simulate_scenario(historia, esc, as_of_date=date(2026, 9, 27))

    # Recalculated weeks at retirement age must NOT include the 940 days from 2020-06-01 to 2022-12-31!
    # 850 + 15 = 865 days / 7 = ~123.57 weeks
    assert res.semanas_totales_a_la_edad < Decimal("150.0"), (
        f"Post-horizon weeks were included in semanas_totales_a_la_edad: {res.semanas_totales_a_la_edad}"
    )


# ---------------------------------------------------------------------------
# Test G: No automatic max(semanas_doc, semanas_cal)
# ---------------------------------------------------------------------------
def test_reproduce_issue_g_no_arbitrary_max_weeks():
    """When semanas_doc (1290) < 1300 but semanas_cal (1310) >= 1300, system must NOT automatically pick max to grant pension without review."""
    engine = PensionEngine()
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-TEST-G",
        fecha_nacimiento=date(1964, 1, 1),
        sexo=SexCategory.MASCULINO,
        semanas_resumen_colpensiones=Decimal(
            1290
        ),  # Not eligible according to Colpensiones summary!
        registros=[
            CotizacionRecord(
                periodo_inicio=date(1995, 1, 1),
                periodo_fin=date(2020, 1, 31),
                dias_reportados=9170,
                dias_cotizados=9170,  # 9170 / 7 = 1310 weeks
                ibc=Decimal(2500000),
                aportante="EMPRESA UNICA",
            )
        ],
    )
    esc = EscenarioConfig("esc1", "Escenario", Decimal(2000000), date(2026, 1, 1))
    res = engine.simulate_scenario(historia, esc, as_of_date=date(2026, 9, 27))

    # Must require review and NOT grant pension automatically through arbitrary max()
    assert (
        getattr(res, "requiere_revision_discrepancia", False) is True
        or res.mesada_bruta is None
        or "discrepancia" in res.mensaje_advertencia.lower()
    )


# ---------------------------------------------------------------------------
# Test H: Do not invent missing days in PDF
# ---------------------------------------------------------------------------
def test_reproduce_issue_h_missing_days_not_invented_as_31():
    """Row '01/01/2024 31/01/2024 $ 3.000.000 EMPRESA' without days must NOT be assigned 31 days."""
    pdf_bytes = create_synthetic_colpensiones_pdf(
        records_lines=[
            "01/01/2024 31/01/2024 $ 3.000.000 EMPRESA",
        ]
    )
    historia, report = ColpensionesPDFReader.extract_from_bytes(pdf_bytes)
    assert historia is not None
    assert len(historia.registros) == 1
    rec = historia.registros[0]
    # The days should be flagged as unverified/pending, NOT automatically assumed to be 31!
    assert (
        rec.dias_cotizados is None
        or getattr(rec, "dias_pendientes_validacion", False) is True
    ), f"Missing days was automatically invented as {rec.dias_cotizados}!"
    assert any("inciert" in w.lower() or "días" in w.lower() for w in report.warnings)


# ---------------------------------------------------------------------------
# Test I: Eliminate silent IPC substitutions
# ---------------------------------------------------------------------------
def test_reproduce_issue_i_no_silent_annual_average_ipc(
    monkeypatch: pytest.MonkeyPatch,
):
    """get_ipc(2018, 2) must not return annual average 85.300; missing months must raise IPCFaltanteError and block scenario."""
    from src.economic.ipc import IPC_SERIES_BASE_2018, IPCFaltanteError

    # 1. 2018-02 must be the verified official DANE index, never the 85.300 annual average
    ipc_2018_2 = get_ipc(2018, 2)
    assert ipc_2018_2 != Decimal("85.300"), (
        "get_ipc(2018, 2) returned the annual average 85.300!"
    )
    assert ipc_2018_2 == Decimal("87.726")

    # 2. Test absence of a month within a year that has other months available
    # Remove May 2018 from series to simulate an unrecorded month
    monkeypatch.delitem(IPC_SERIES_BASE_2018, (2018, 5), raising=False)
    with pytest.raises(IPCFaltanteError) as exc_info:
        get_ipc(2018, 5)
    assert exc_info.value.year == 2018 and exc_info.value.month == 5
    assert "no disponible" in str(exc_info.value).lower()

    # 3. Engine simulation must catch this and return a blocked result, not an unhandled crash
    engine = PensionEngine()
    recs = [
        CotizacionRecord(
            periodo_inicio=date(1995, 1, 1),
            periodo_fin=date(2018, 4, 30),
            dias_reportados=8500,
            dias_cotizados=8500,
            ibc=Decimal(2000000),
            aportante="EMP BASE",
        ),
        CotizacionRecord(
            periodo_inicio=date(2018, 5, 1),
            periodo_fin=date(2018, 5, 31),
            dias_reportados=30,
            dias_cotizados=30,
            ibc=Decimal(3000000),
            aportante="EMP IPC",
        ),
        CotizacionRecord(
            periodo_inicio=date(2018, 6, 1),
            periodo_fin=date(2020, 1, 31),
            dias_reportados=570,
            dias_cotizados=570,
            ibc=Decimal(3000000),
            aportante="EMP FINAL",
        ),
    ]
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-IPC",
        fecha_nacimiento=date(1964, 1, 1),
        sexo=SexCategory.MASCULINO,
        semanas_resumen_colpensiones=Decimal(1300),
        registros=recs,
    )
    esc = EscenarioConfig("esc_ipc", "Escenario", Decimal(3000000), date(2026, 1, 1))
    res = engine.simulate_scenario(historia, esc, as_of_date=date(2026, 9, 27))
    assert res.mesada_bruta is None, (
        "Mesada must not be calculated when historical IPC is missing"
    )
    assert (
        "ipc" in res.mensaje_advertencia.lower()
        or res.limite_aplicado == "BLOQUEADO_POR_IPC_FALTANTE"
    )
    assert res.bloqueado_por_ipc is True
