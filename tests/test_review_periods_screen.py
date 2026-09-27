"""Tests for the 'Revisar períodos y semanas' screen, validation engine,
record exclusion/restoration, and reconciliation summary.
Conforms to AGENTS.md and TDD.
"""

from datetime import date
from decimal import Decimal

from src.domain.models import (
    CotizacionRecord,
    EscenarioConfig,
    HistoriaLaboral,
    ProvenanceType,
    ResumenEmpleadorRecord,
    SexCategory,
)
from src.domain.pension_engine import PensionEngine
from src.domain.validation import (
    reconcile_labor_history,
    validate_cotizacion_record,
    validate_labor_history_periods,
)


def test_record_validation_inverted_dates() -> None:
    """Detects inverted dates where periodo_inicio > periodo_fin."""
    rec = CotizacionRecord(
        periodo_inicio=date(2025, 6, 30),
        periodo_fin=date(2025, 6, 1),  # Inverted!
        dias_reportados=30,
        dias_cotizados=30,
        ibc=Decimal(2000000),
        aportante="EMPRESA INVERTIDA",
    )
    issues = validate_cotizacion_record(rec)
    error_codes = [issue["code"] for issue in issues]
    assert "FECHAS_INVERTIDAS" in error_codes


def test_record_validation_negative_values() -> None:
    """Detects negative days or negative IBC."""
    rec_neg_dias = CotizacionRecord(
        periodo_inicio=date(2025, 1, 1),
        periodo_fin=date(2025, 1, 31),
        dias_reportados=-10,
        dias_cotizados=-10,
        ibc=Decimal(2000000),
        aportante="EMPRESA NEGATIVA",
    )
    issues_dias = validate_cotizacion_record(rec_neg_dias)
    assert any(i["code"] == "VALOR_NEGATIVO_DIAS" for i in issues_dias)

    rec_neg_ibc = CotizacionRecord(
        periodo_inicio=date(2025, 1, 1),
        periodo_fin=date(2025, 1, 31),
        dias_reportados=30,
        dias_cotizados=30,
        ibc=Decimal(-500000),
        aportante="EMPRESA NEGATIVA",
    )
    issues_ibc = validate_cotizacion_record(rec_neg_ibc)
    assert any(i["code"] == "VALOR_NEGATIVO_IBC" for i in issues_ibc)


def test_record_validation_incompatible_days() -> None:
    """Detects days exceeding the calendar span of the period."""
    # February 2025 has 28 days
    rec_exceeding = CotizacionRecord(
        periodo_inicio=date(2025, 2, 1),
        periodo_fin=date(2025, 2, 28),
        dias_reportados=35,
        dias_cotizados=35,  # Exceeds 28 calendar days!
        ibc=Decimal(2000000),
        aportante="EMPRESA EXCESO",
    )
    issues = validate_cotizacion_record(rec_exceeding)
    assert any(i["code"] == "DIAS_INCOMPATIBLES_CON_PERIODO" for i in issues)


def test_record_validation_missing_vs_zero_ibc() -> None:
    """Distinguishes missing IBC (not informed) from explicit zero IBC."""
    rec_zero_ibc = CotizacionRecord(
        periodo_inicio=date(2025, 3, 1),
        periodo_fin=date(2025, 3, 31),
        dias_reportados=30,
        dias_cotizados=30,
        ibc=Decimal(0),  # Explicit zero
        aportante="EMPRESA LICENCIA",
    )
    issues_zero = validate_cotizacion_record(rec_zero_ibc)
    # Zero is allowed (e.g. non-remunerated leaves) but raises informational note, not fatal missing
    assert not any(i["code"] == "DATO_AUSENTE_IBC" for i in issues_zero)

    # Missing IBC handled via validation dictionary or flags
    rec_missing = CotizacionRecord(
        periodo_inicio=date(2025, 3, 1),
        periodo_fin=date(2025, 3, 31),
        dias_reportados=30,
        dias_cotizados=30,
        ibc=Decimal(0),
        aportante="EMPRESA VACIA",
        observaciones="SIN_IBC_INFORMADO",
        dias_pendientes_validacion=True,
    )
    issues_missing = validate_cotizacion_record(rec_missing)
    assert any(i["code"] == "REQUIERE_REVISION_DATOS" for i in issues_missing)


def test_record_validation_duplicates_and_overlaps() -> None:
    """Detects exact duplicate records and overlapping intervals for the same employer."""
    rec1 = CotizacionRecord(
        periodo_inicio=date(2025, 1, 1),
        periodo_fin=date(2025, 1, 31),
        dias_reportados=30,
        dias_cotizados=30,
        ibc=Decimal(2000000),
        aportante="EMPRESA DUPLICADA",
    )
    rec2 = CotizacionRecord(
        periodo_inicio=date(2025, 1, 1),
        periodo_fin=date(2025, 1, 31),
        dias_reportados=30,
        dias_cotizados=30,
        ibc=Decimal(2000000),
        aportante="EMPRESA DUPLICADA",
    )
    issues = validate_labor_history_periods([rec1, rec2])
    assert any(i["code"] == "REGISTRO_DUPLICADO" for i in issues)


def test_reconciliation_summary_metrics() -> None:
    """Reconciliation over tables shows recognized, recalculated, declared, and differences,

    without automatically choosing the maximum.
    """
    rec_pdf = CotizacionRecord(
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=date(2024, 12, 31),
        dias_reportados=360,
        dias_cotizados=366,  # 366 / 7 = 52.285 weeks
        ibc=Decimal(2500000),
        aportante="EMPRESA PDF",
        origen=ProvenanceType.PDF,
    )
    rec_declared = CotizacionRecord(
        periodo_inicio=date(2025, 1, 1),
        periodo_fin=date(2025, 6, 30),
        dias_reportados=180,
        dias_cotizados=181,  # 181 / 7 = 25.857 weeks
        ibc=Decimal(3000000),
        aportante="EMPRESA DECLARADA",
        origen=ProvenanceType.DECLARACION_USUARIO,
    )

    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-RECON-1",
        fecha_nacimiento=date(1964, 1, 1),
        sexo=SexCategory.MASCULINO,
        semanas_resumen_colpensiones=Decimal("1200.00"),  # Recognized in PDF header
        registros=[rec_pdf, rec_declared],
    )

    recon = reconcile_labor_history(historia)

    # 1. Recognized in PDF
    assert recon["semanas_reconocidas_pdf"] == Decimal("1200.00")
    # 2. Recalculated from detail (PDF only)
    assert recon["semanas_recalculadas_detalle"] == Decimal("52.29")
    # 3. Additional user declared
    assert recon["semanas_declaradas_adicionales"] == Decimal("25.86")
    # 4. Total active considered
    assert recon["semanas_totales_activas"] == Decimal("78.14")
    # 5. Difference between recognized and detail
    assert recon["diferencia_detalle_vs_reconocidas"] != Decimal(0)
    # 6. Flag indicating pending discrepancy
    assert recon["tiene_discrepancia"] is True
    # 7. Crucial rule: does NOT arbitrarily select the maximum!
    assert recon["semanas_totales_activas"] != max(Decimal("1200.00"), Decimal("78.15"))


def test_ultimo_salario_not_converted_to_historical_monthly_ibc() -> None:
    """Summary table 'ultimo_salario' must not be converted to monthly IBC

    of all periods nor replace historical cotizaciones.
    """
    summary = ResumenEmpleadorRecord(
        nit="890100200",
        nombre_aportante="BANCO NACIONAL",
        periodo_inicio=date(2010, 1, 1),
        periodo_fin=date(2020, 12, 31),
        ultimo_salario=Decimal(8500000),
        semanas=Decimal(500),
        total_semanas=Decimal(500),
    )
    detail_rec = CotizacionRecord(
        periodo_inicio=date(2015, 6, 1),
        periodo_fin=date(2015, 6, 30),
        dias_reportados=30,
        dias_cotizados=30,
        ibc=Decimal(2000000),  # Real historical IBC
        aportante="BANCO NACIONAL",
    )
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-SALARIO-1",
        fecha_nacimiento=date(1964, 1, 1),
        sexo=SexCategory.MASCULINO,
        resumen_empleadores=[summary],
        registros=[detail_rec],
    )

    engine = PensionEngine()
    monthly = engine.build_monthly_cotizaciones(historia.registros)

    # Must preserve the exact 2,000,000 IBC and NOT overwrite with 8,500,000
    june_2015 = next(m for m in monthly if m["year"] == 2015 and m["month"] == 6)
    assert june_2015["ibc"] == Decimal(2000000)


def test_summary_and_detail_not_summed_as_independent_contributions() -> None:
    """Summary and detail must not be added together as independent weeks."""
    summary = ResumenEmpleadorRecord(
        nit="900111222",
        nombre_aportante="CORP EMPRESARIAL",
        periodo_inicio=date(2018, 1, 1),
        periodo_fin=date(2018, 12, 31),
        ultimo_salario=Decimal(3000000),
        semanas=Decimal(52),
        total_semanas=Decimal(52),
    )
    # Detail covering the exact same period
    detail = CotizacionRecord(
        periodo_inicio=date(2018, 1, 1),
        periodo_fin=date(2018, 12, 31),
        dias_reportados=360,
        dias_cotizados=365,
        ibc=Decimal(3000000),
        aportante="CORP EMPRESARIAL",
    )
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-NODUP-1",
        fecha_nacimiento=date(1964, 1, 1),
        sexo=SexCategory.MASCULINO,
        resumen_empleadores=[summary],
        registros=[detail],
    )

    engine = PensionEngine()
    cal_weeks = engine.compute_calendar_weeks(historia.registros)

    # 365 days / 7 = 52.14 weeks. Summary 52 weeks is NOT added to make 104 weeks!
    assert cal_weeks < Decimal("60.00")
    assert cal_weeks == Decimal("52.14")


def test_record_exclusion_and_restoration() -> None:
    """User can exclude a record from calculation and later restore it."""
    rec1 = CotizacionRecord(
        periodo_inicio=date(2023, 1, 1),
        periodo_fin=date(2023, 6, 30),
        dias_reportados=180,
        dias_cotizados=181,
        ibc=Decimal(2500000),
        aportante="EMPRESA EXCLUIR",
        excluido_del_calculo=False,
    )
    rec2 = CotizacionRecord(
        periodo_inicio=date(2023, 7, 1),
        periodo_fin=date(2023, 12, 31),
        dias_reportados=180,
        dias_cotizados=184,
        ibc=Decimal(2500000),
        aportante="EMPRESA EXCLUIR",
        excluido_del_calculo=False,
    )

    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-EXCL-1",
        fecha_nacimiento=date(1964, 1, 1),
        sexo=SexCategory.MASCULINO,
        registros=[rec1, rec2],
    )

    engine = PensionEngine()
    weeks_both = engine.compute_calendar_weeks(historia.registros)

    # Exclude rec2
    rec2_excluded = CotizacionRecord(
        periodo_inicio=rec2.periodo_inicio,
        periodo_fin=rec2.periodo_fin,
        dias_reportados=rec2.dias_reportados,
        dias_cotizados=rec2.dias_cotizados,
        ibc=rec2.ibc,
        aportante=rec2.aportante,
        excluido_del_calculo=True,
        motivo_exclusion="Período no reconocido por Colpensiones en demanda",
    )
    historia.registros = [rec1, rec2_excluded]
    weeks_after_exclusion = engine.compute_calendar_weeks(historia.registros)

    assert weeks_after_exclusion < weeks_both
    # Only rec1 computed: 181 / 7 = 25.85 weeks (ROUND_FLOOR)
    assert weeks_after_exclusion == Decimal("25.85")

    # Restore rec2
    rec2_restored = CotizacionRecord(
        periodo_inicio=rec2.periodo_inicio,
        periodo_fin=rec2.periodo_fin,
        dias_reportados=rec2.dias_reportados,
        dias_cotizados=rec2.dias_cotizados,
        ibc=rec2.ibc,
        aportante=rec2.aportante,
        excluido_del_calculo=False,
        estado_validacion="RESTAURADO",
    )
    historia.registros = [rec1, rec2_restored]
    weeks_restored = engine.compute_calendar_weeks(historia.registros)
    assert weeks_restored == weeks_both


def test_revision_tracking_in_simulation_audit() -> None:
    """Simulation audit identifies which data revision version was used

    and breaks down provenance counts with disclaimer on manual edits.
    """
    rec_pdf = CotizacionRecord(
        periodo_inicio=date(2005, 1, 1),
        periodo_fin=date(2025, 1, 1),
        dias_reportados=7300,
        dias_cotizados=7300,  # ~1042 weeks
        ibc=Decimal(3500000),
        aportante="EMPRESA AUDIT REV",
        origen=ProvenanceType.PDF,
    )
    rec_corr = CotizacionRecord(
        periodo_inicio=date(2025, 1, 2),
        periodo_fin=date(2025, 6, 30),
        dias_reportados=180,
        dias_cotizados=180,
        ibc=Decimal(4000000),
        aportante="EMPRESA AUDIT REV",
        origen=ProvenanceType.CORRECCION_MANUAL,
        motivo_correccion="Ajuste de IBC según desprendible de nómina",
    )
    rec_excl = CotizacionRecord(
        periodo_inicio=date(2025, 7, 1),
        periodo_fin=date(2025, 7, 31),
        dias_reportados=30,
        dias_cotizados=30,
        ibc=Decimal(4000000),
        aportante="EMPRESA AUDIT REV",
        excluido_del_calculo=True,
        motivo_exclusion="Pago duplicado",
    )

    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-REV-AUDIT",
        fecha_nacimiento=date(1964, 1, 1),
        sexo=SexCategory.MASCULINO,
        revision_version=3,
        revision_id="rev_20260927_003",
        registros=[rec_pdf, rec_corr, rec_excl],
    )

    engine = PensionEngine()
    esc = EscenarioConfig(
        escenario_id="esc_rev_test",
        nombre="Escenario Revision",
        ibc_futuro_inicial=Decimal(3500000),
        fecha_inicio_ibc=date(2025, 8, 1),
    )

    exec_id = "test-exec-revision-audit"
    res = engine.simulate_scenario(
        historia, esc, as_of_date=date(2025, 8, 1), execution_id=exec_id
    )
    assert res is not None

    from src.audit.service import AuditService

    audit = AuditService.get_or_create_audit(exec_id)
    sc_audit = next(s for s in audit.scenarios_audit if s.scenario_id == "esc_rev_test")

    # Verify data version used is explicitly recorded in audit
    assert sc_audit.data_version_used is not None
    assert "rev_20260927_003" in sc_audit.data_version_used
    assert (
        "Rev 3" in sc_audit.data_version_used
        or "v3" in sc_audit.data_version_used.lower()
    )

    # Provenance breakdown
    assert sc_audit.provenance_counts["PDF"] == 1
    assert sc_audit.provenance_counts["CORRECCION_MANUAL"] == 1
    assert sc_audit.provenance_counts["EXCLUIDO"] == 1

    # Disclaimer note present
    assert "no constituyen certificaciones" in sc_audit.legal_disclaimer.lower()
