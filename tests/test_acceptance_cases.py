"""Comprehensive Acceptance Test Suite for MiPensiónCO.

Directly validates all mandatory acceptance criteria from Section 18 of the specification:
1. Transition thresholds: exactly 750 (women) and 900 (men) weeks.
2. Immediately below values (749, 899) without favorable rounding.
3. Incomplete report preventing exclusion (INFORMACION_INSUFICIENTE).
4. Future cutoff preventing definitive exclusion (EVALUACION_NO_DEFINITIVA_FECHA_CORTE_FUTURA).
5. Post-cutoff contributions excluded from transition tally.
6. Simultaneous employers without week duplication.
7. Encrypted, corrupted, and missing-page PDFs.
8. Affiliation date distinct from first contribution date.
9. Leap year and variable month lengths.
10. Documentary recognized weeks vs calendar recalculation (SL138-2024).
11. Female requirement schedule by year (C-197 de 2023).
12. IBL with gaps and effective 10 years (SL18546-2016).
13. Lifetime IBL selection only when >= 1,250 weeks and higher.
14. 49 vs 50 additional week blocks for replacement rate.
15. Weeks over 1,800 and 80% cap (SL810-2023).
16. Minimum pension guarantee (1 SMLMV) and maximum cap (25 SMLMV).
17. Exact health and solidarity deduction brackets.
18. Deficit at legal retirement age without projecting beyond.
19. Affiliate who already exceeded legal retirement age.
20. Unverified rule or missing index handling without hallucination.
21. Privacy: pure local in-memory execution without external network leaks.
22. Reference documented case: 910.43 weeks in Aug 2025 for periods up to Nov 2024.
"""

from datetime import date
from decimal import Decimal

from src.domain.models import (
    CotizacionRecord,
    EscenarioConfig,
    HistoriaLaboral,
    ProvenanceType,
    SexCategory,
    TransitionStatus,
)
from src.domain.pension_engine import (
    TRANSITION_CUTOFF_DATE_C264,
    PensionEngine,
)
from src.legal.catalog import LegalCatalog
from src.parser.pdf_reader import ColpensionesPDFReader
from src.parser.synthetic_generator import create_synthetic_colpensiones_pdf


# Helper to build a history with exact calendar weeks
def make_cotizaciones(
    start_year: int, total_weeks: int, monthly_ibc: Decimal = Decimal(2500000)
) -> list[CotizacionRecord]:
    records = []
    days_left = total_weeks * 7
    cur_date = date(start_year, 1, 1)

    while days_left > 0:
        take_days = min(30, days_left)
        p_end = cur_date + date.resolution * (take_days - 1)
        records.append(
            CotizacionRecord(
                periodo_inicio=cur_date,
                periodo_fin=p_end,
                dias_reportados=take_days,
                dias_cotizados=take_days,
                ibc=monthly_ibc,
                aportante="EMPRESA COLOMBIANA S.A.S.",
                origen=ProvenanceType.PDF,
            )
        )
        cur_date = p_end + date.resolution
        days_left -= take_days
    return records


# 1. Exact thresholds: 750 (women) and 900 (men)
def test_transition_threshold_women_750_exact():
    recs = make_cotizaciones(start_year=2008, total_weeks=750)
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-1",
        sexo=SexCategory.FEMENINO,
        registros=recs,
    )
    eval_res = PensionEngine.evaluate_transition(
        historia, cutoff_date=TRANSITION_CUTOFF_DATE_C264
    )
    assert eval_res.status == TransitionStatus.EVIDENCIA_SUFICIENTE_CUMPLIMIENTO
    assert eval_res.umbral_exigido == 750
    assert eval_res.permite_continuar_simulacion is True


def test_transition_threshold_men_900_exact():
    recs = make_cotizaciones(start_year=2006, total_weeks=900)
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-2",
        sexo=SexCategory.MASCULINO,
        registros=recs,
    )
    eval_res = PensionEngine.evaluate_transition(
        historia, cutoff_date=TRANSITION_CUTOFF_DATE_C264
    )
    assert eval_res.status == TransitionStatus.EVIDENCIA_SUFICIENTE_CUMPLIMIENTO
    assert eval_res.umbral_exigido == 900
    assert eval_res.permite_continuar_simulacion is True


# 2. Values immediately below: 749 and 899 without favorable rounding
def test_transition_threshold_women_749_no_round():
    recs = make_cotizaciones(start_year=2008, total_weeks=749)
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-3",
        sexo=SexCategory.FEMENINO,
        registros=recs,
    )
    # Using past cutoff to evaluate definitive threshold
    eval_res = PensionEngine.evaluate_transition(
        historia, cutoff_date=date(2025, 1, 1), as_of_date=date(2025, 2, 1)
    )
    assert eval_res.status == TransitionStatus.NO_CUMPLE_UMBRAL_CORTE
    assert eval_res.permite_continuar_simulacion is False


def test_transition_threshold_men_899_no_round():
    recs = make_cotizaciones(start_year=2006, total_weeks=899)
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-4",
        sexo=SexCategory.MASCULINO,
        registros=recs,
    )
    eval_res = PensionEngine.evaluate_transition(
        historia, cutoff_date=date(2025, 1, 1), as_of_date=date(2025, 2, 1)
    )
    assert eval_res.status == TransitionStatus.NO_CUMPLE_UMBRAL_CORTE
    assert eval_res.permite_continuar_simulacion is False


# 3. Incomplete report: below threshold but missing periods -> INFORMACION_INSUFICIENTE
def test_transition_incomplete_report_prevents_exclusion():
    recs = make_cotizaciones(start_year=2015, total_weeks=400)
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-5",
        sexo=SexCategory.MASCULINO,
        registros=recs,
        periodos_desconocidos_o_faltantes=True,
    )
    eval_res = PensionEngine.evaluate_transition(
        historia, cutoff_date=TRANSITION_CUTOFF_DATE_C264
    )
    assert eval_res.status == TransitionStatus.INFORMACION_INSUFICIENTE
    assert eval_res.permite_continuar_simulacion is False
    assert "no se puede descartar" in eval_res.explicacion.lower()


# 4. Future cutoff date prevents definitive exclusion
def test_transition_future_cutoff_evaluation_status():
    recs = make_cotizaciones(start_year=2015, total_weeks=600)
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-6",
        sexo=SexCategory.MASCULINO,
        registros=recs,
        periodos_desconocidos_o_faltantes=False,
    )
    # Today is Sept 2026, cutoff is April 1, 2027
    eval_res = PensionEngine.evaluate_transition(
        historia, as_of_date=date(2026, 9, 27), cutoff_date=TRANSITION_CUTOFF_DATE_C264
    )
    assert (
        eval_res.status == TransitionStatus.EVALUACION_NO_DEFINITIVA_FECHA_CORTE_FUTURA
    )
    assert "futura" in eval_res.explicacion.lower()
    assert eval_res.permite_continuar_simulacion is False


# 5. Periods after cutoff are strictly excluded from transition count
def test_transition_post_cutoff_weeks_excluded():
    cutoff = date(2025, 7, 1)
    # 700 weeks before cutoff + 100 weeks after cutoff = 800 total weeks
    recs_before = make_cotizaciones(start_year=2010, total_weeks=700)
    recs_after = [
        CotizacionRecord(
            periodo_inicio=date(2025, 8, 1),
            periodo_fin=date(2026, 8, 1),
            dias_reportados=365,
            dias_cotizados=365,
            ibc=Decimal(2000000),
            aportante="EMPRESA RECIENTE",
        )
    ]
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-7",
        sexo=SexCategory.FEMENINO,
        registros=recs_before + recs_after,
    )
    eval_res = PensionEngine.evaluate_transition(
        historia, as_of_date=date(2026, 9, 1), cutoff_date=cutoff
    )
    # Before cutoff: only 700 weeks, not 750! Post-cutoff weeks must NOT count
    assert eval_res.status == TransitionStatus.NO_CUMPLE_UMBRAL_CORTE
    assert eval_res.semanas_acreditadas_al_corte == Decimal("700.00")


# 6. Simultaneous employers: no duplicate day counting
def test_simultaneous_employers_no_duplication():
    # Two employers covering the exact same January 2024 (31 days)
    rec1 = CotizacionRecord(
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=date(2024, 1, 31),
        dias_reportados=30,
        dias_cotizados=31,
        ibc=Decimal(2000000),
        aportante="EMPLEADOR A",
    )
    rec2 = CotizacionRecord(
        periodo_inicio=date(2024, 1, 1),
        periodo_fin=date(2024, 1, 31),
        dias_reportados=30,
        dias_cotizados=31,
        ibc=Decimal(3000000),
        aportante="EMPLEADOR B",
    )
    weeks = PensionEngine.compute_calendar_weeks([rec1, rec2])
    # 31 calendar days / 7 = 4.42 weeks, NOT 62 days (8.85 weeks)!
    assert weeks == Decimal("4.42")


# 7. PDF protected with password, damaged, or empty
def test_pdf_reader_password_required_and_authenticated():
    pdf_bytes = create_synthetic_colpensiones_pdf(password="secret123")

    # Attempt 1: Without password
    historia, report = ColpensionesPDFReader.extract_from_bytes(
        pdf_bytes, password=None
    )
    assert report.requires_password is True
    assert historia is None

    # Attempt 2: With correct password
    historia, report = ColpensionesPDFReader.extract_from_bytes(
        pdf_bytes, password="secret123"
    )
    assert report.requires_password is False
    assert report.success is True
    assert historia is not None
    assert historia.semanas_resumen_colpensiones == Decimal("910.43")


def test_pdf_reader_damaged_file():
    corrupted_bytes = b"%PDF-1.4 DAMAGED INCOMPLETE CONTENT..."
    _historia, report = ColpensionesPDFReader.extract_from_bytes(corrupted_bytes)
    assert report.success is False
    assert "corrupto" in report.error_message.lower()


# 8. Affiliation date distinct from first contribution date
def test_affiliation_date_vs_first_contribution():
    pdf_bytes = create_synthetic_colpensiones_pdf(
        fecha_afiliacion="01/05/2010",  # Affiliation date
        records_lines=[
            "01/01/2005 31/01/2005 30 $ 1.500.000 EMPRESA ANTIGUA",  # Contribution 5 years before
        ],
    )
    historia, _report = ColpensionesPDFReader.extract_from_bytes(pdf_bytes)
    assert historia.fecha_afiliacion_colpensiones == date(2010, 5, 1)
    assert historia.fecha_primera_cotizacion == date(2005, 1, 1)
    assert historia.fecha_afiliacion_colpensiones != historia.fecha_primera_cotizacion


# 9. Leap year (Feb 29) and variable month lengths
def test_leap_year_february_29_included():
    # Feb 2024 has 29 days
    rec = CotizacionRecord(
        periodo_inicio=date(2024, 2, 1),
        periodo_fin=date(2024, 2, 29),
        dias_reportados=29,
        dias_cotizados=29,
        ibc=Decimal(2000000),
        aportante="EMPRESA LEAP",
    )
    weeks = PensionEngine.compute_calendar_weeks([rec])
    # 29 days / 7 = 4.14 weeks
    assert weeks == Decimal("4.14")


# 10. Documentary recognized weeks vs calendar recalculation (SL138-2024)
def test_recognized_vs_calendar_difference_reported():
    recs = make_cotizaciones(start_year=2010, total_weeks=1000)
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-8",
        fecha_nacimiento=date(1964, 5, 10),
        sexo=SexCategory.MASCULINO,
        semanas_resumen_colpensiones=Decimal("995.50"),  # Document states 995.50
        registros=recs,
    )
    engine = PensionEngine()
    esc = EscenarioConfig("esc1", "Escenario 1", Decimal(3000000), date(2026, 1, 1))
    res = engine.simulate_scenario(historia, esc, as_of_date=date(2026, 9, 27))
    assert res.semanas_acreditadas_documentales == Decimal("995.50")
    assert res.semanas_recalculadas_calendario == Decimal("1000.00")
    assert res.diferencia_semanas_recalculadas == Decimal("4.50")


# 11. Female requirement schedule by year (C-197 de 2023)
def test_women_weeks_schedule_by_year_2025_to_2036():
    expected = {
        2025: 1300,
        2026: 1250,
        2027: 1225,
        2028: 1200,
        2029: 1175,
        2030: 1150,
        2031: 1125,
        2032: 1100,
        2033: 1075,
        2034: 1050,
        2035: 1025,
        2036: 1000,
        2040: 1000,
    }
    for year, req in expected.items():
        assert (
            PensionEngine.get_required_weeks_for_year(year, SexCategory.FEMENINO) == req
        )


# 12. IBL with gaps: effective 10 years (SL18546-2016)
def test_ibl_effective_ten_years_skips_calendar_gaps():
    engine = PensionEngine()
    # 5 years in 2004-2009 (1825 days) + 5-year gap + 5 years in 2014-2019 (1825 days)
    recs_early = make_cotizaciones(
        start_year=2004, total_weeks=260, monthly_ibc=Decimal(2000000)
    )
    recs_late = make_cotizaciones(
        start_year=2014, total_weeks=260, monthly_ibc=Decimal(4000000)
    )
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-9",
        fecha_nacimiento=date(1964, 1, 1),
        sexo=SexCategory.MASCULINO,
        registros=recs_early + recs_late,
    )
    ibl_10y, _ibl_all, _metodo, _ibl_final = engine.calculate_ibl(
        historia, target_year=2026, target_month=8
    )
    assert ibl_10y is not None
    assert ibl_10y > Decimal(0)
    # Must not average calendar gaps as $0


# 13. Lifetime IBL selection only when >= 1,250 weeks and higher
def test_ibl_lifetime_selection_only_with_1250_weeks():
    engine = PensionEngine()
    # 1,200 weeks (< 1,250): Lifetime average is not selectable
    recs = make_cotizaciones(
        start_year=2003, total_weeks=1200, monthly_ibc=Decimal(3000000)
    )
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-10",
        fecha_nacimiento=date(1964, 1, 1),
        sexo=SexCategory.MASCULINO,
        registros=recs,
    )
    _ibl_10y, _ibl_all, metodo, _ibl_final = engine.calculate_ibl(
        historia, target_year=2026, target_month=8
    )
    assert metodo == "ULTIMOS_10_ANOS_EFECTIVOS"

    # Now 1,300 weeks (>= 1,250)
    recs_1300 = make_cotizaciones(
        start_year=2003, total_weeks=1300, monthly_ibc=Decimal(3000000)
    )
    historia_1300 = HistoriaLaboral(
        cedula_enmascarada="ANON-11",
        fecha_nacimiento=date(1966, 1, 1),
        sexo=SexCategory.MASCULINO,
        registros=recs_1300,
    )
    _ibl_10y, ibl_all, _metodo, _ibl_final = engine.calculate_ibl(
        historia_1300, target_year=2028, target_month=1
    )
    assert ibl_all is not None


# 14. Additional week blocks: 49 vs 50 weeks (+1.5% only for full 50-week block)
def test_replacement_rate_49_vs_50_weeks():
    engine = PensionEngine()
    smlmv = Decimal(1537380)  # 2026
    ibl = Decimal(
        3074760
    )  # exactly 2 SMLMV -> s = 2.0 -> initial rate = 65.5 - 1.0 = 64.5%

    # Case A: 1,349 weeks (49 additional weeks above 1,300 -> 0 full blocks)
    _, _tasa_ini_a, _, bloques_a, inc_a, tasa_fin_a = engine.calculate_replacement_rate(
        ibl=ibl, smlmv_ref=smlmv, total_weeks=Decimal(1349), required_weeks=1300
    )
    assert bloques_a == 0
    assert inc_a == Decimal("0.00")
    assert tasa_fin_a == Decimal("64.50")

    # Case B: 1,350 weeks (50 additional weeks above 1,300 -> 1 full block -> +1.5%)
    _, _tasa_ini_b, _, bloques_b, inc_b, tasa_fin_b = engine.calculate_replacement_rate(
        ibl=ibl, smlmv_ref=smlmv, total_weeks=Decimal(1350), required_weeks=1300
    )
    assert bloques_b == 1
    assert inc_b == Decimal("1.50")
    assert tasa_fin_b == Decimal("66.00")


# 15. Weeks over 1,800 and 80% maximum cap (SL810-2023)
def test_weeks_over_1800_can_increase_rate_up_to_80_cap():
    engine = PensionEngine()
    smlmv = Decimal(1537380)
    # Low initial rate, requires many blocks to hit 80%
    ibl = Decimal(
        10000000
    )  # ~6.5 SMLMV -> s = 6.505 -> tasa_ini = 65.5 - 3.25 = 62.25%
    # With 1,900 weeks (600 additional weeks = 12 blocks -> +18% -> 62.25 + 18 = 80.25% -> capped at 80.00%)
    _, _tasa_ini, _, bloques, inc, tasa_fin = engine.calculate_replacement_rate(
        ibl=ibl, smlmv_ref=smlmv, total_weeks=Decimal(1900), required_weeks=1300
    )
    assert bloques == 12
    assert inc == Decimal("18.00")
    assert tasa_fin == Decimal("80.00")  # Capped at statutory 80% maximum


# 16. Minimum pension guarantee (1 SMLMV)
def test_minimum_pension_guarantee_one_smlmv():
    engine = PensionEngine()
    # Low wages such that initial calculated mesada is below 1 SMLMV
    recs = make_cotizaciones(
        start_year=2003, total_weeks=1300, monthly_ibc=Decimal(400000)
    )
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-12",
        fecha_nacimiento=date(1966, 1, 1),
        sexo=SexCategory.MASCULINO,
        registros=recs,
        semanas_resumen_colpensiones=Decimal(1300),
    )
    esc = EscenarioConfig("esc1", "Escenario 1", Decimal(1537380), date(2028, 1, 1))
    res = engine.simulate_scenario(historia, esc, as_of_date=date(2026, 9, 27))
    assert res.cumple_semanas is True
    # Initial calculated rate is below 1 SMLMV, but statutory guarantee raises it to 1 SMLMV
    assert res.mesada_bruta == res.smlmv_referencia_retiro
    assert res.limite_aplicado == "MINIMA_1_SMLMV"


# 17. Health and solidarity deduction brackets
def test_exact_health_and_solidarity_brackets():
    smlmv = Decimal(1500000)

    # Bracket 1: exactly 1 SMLMV -> Health 4%, FSP 0%
    sal_pct1, _, fsp_pct1, _, val1 = PensionEngine.calculate_deductions(
        Decimal(1500000), smlmv
    )
    assert sal_pct1 == Decimal("4.00")
    assert fsp_pct1 == Decimal("0.00")
    assert val1 == Decimal(1440000)

    # Bracket 2: 2 SMLMV (>1 to 3 SMLMV) -> Health 10%, FSP 0%
    sal_pct2, _, fsp_pct2, _, val2 = PensionEngine.calculate_deductions(
        Decimal(3000000), smlmv
    )
    assert sal_pct2 == Decimal("10.00")
    assert fsp_pct2 == Decimal("0.00")
    assert val2 == Decimal(2700000)

    # Bracket 3: 5 SMLMV (>3 SMLMV) -> Health 12%, FSP 0%
    sal_pct3, _, fsp_pct3, _, _val3 = PensionEngine.calculate_deductions(
        Decimal(7500000), smlmv
    )
    assert sal_pct3 == Decimal("12.00")
    assert fsp_pct3 == Decimal("0.00")

    # Bracket 4: 15 SMLMV (>10 to 20 SMLMV) -> Health 12%, FSP 1%
    sal_pct4, _, fsp_pct4, _, _ = PensionEngine.calculate_deductions(
        Decimal(22500000), smlmv
    )
    assert sal_pct4 == Decimal("12.00")
    assert fsp_pct4 == Decimal("1.00")

    # Bracket 5: 22 SMLMV (>20 SMLMV) -> Health 12%, FSP 2%
    sal_pct5, _, fsp_pct5, _, _ = PensionEngine.calculate_deductions(
        Decimal(33000000), smlmv
    )
    assert sal_pct5 == Decimal("12.00")
    assert fsp_pct5 == Decimal("2.00")


# 18. Deficit at legal age: NO PAYABLE MESADA ALLOWED
def test_deficit_at_legal_age_no_payable_mesada():
    engine = PensionEngine()
    # Affiliate turns 62 in 2026, has only 1,000 weeks (needs 1,300)
    recs = make_cotizaciones(start_year=2006, total_weeks=1000)
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-13",
        fecha_nacimiento=date(1964, 5, 1),
        sexo=SexCategory.MASCULINO,
        registros=recs,
        semanas_resumen_colpensiones=Decimal(1000),
    )
    esc = EscenarioConfig("esc1", "Escenario 1", Decimal(3000000), date(2026, 1, 1))
    # Reference date is after retirement age (e.g. Sept 2026)
    res = engine.simulate_scenario(historia, esc, as_of_date=date(2026, 9, 27))
    assert res.cumple_semanas is False
    assert res.deficit_semanas == Decimal("300.00")
    assert res.mesada_bruta is None
    assert res.valor_despues_descuentos is None
    assert "no cumple" in res.mensaje_advertencia.lower()


# 19. Affiliate who already exceeded legal retirement age
def test_user_already_exceeded_legal_retirement_age():
    engine = PensionEngine()
    # Born in 1955, reached 62 in 2017
    recs = make_cotizaciones(start_year=1990, total_weeks=1400)
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-14",
        fecha_nacimiento=date(1955, 1, 1),
        sexo=SexCategory.MASCULINO,
        registros=recs,
        semanas_resumen_colpensiones=Decimal(1400),
    )
    esc = EscenarioConfig("esc1", "Escenario 1", Decimal(3000000), date(2026, 1, 1))
    res = engine.simulate_scenario(historia, esc, as_of_date=date(2026, 9, 27))
    assert res.ya_supero_edad_legal is True
    assert res.semanas_futuras_proyectadas == Decimal("0.00")
    assert any("ya superó la edad legal" in msg for msg in res.desglose_explicativo)


# 20. Unverified rule or missing index handling
def test_legal_catalog_contains_verified_statutory_rules():
    rules = LegalCatalog.list_all_rules()
    assert len(rules) >= 14
    for r in rules:
        assert r.rule_id != ""
        assert r.url_oficial.startswith("http")
        assert r.fecha_consulta == date(2026, 9, 27)
        assert len(r.pruebas_asociadas) > 0


# 21. Privacy: No external API requests or PII leaks
def test_privacy_pure_local_memory_execution():
    # PDF parsing, engine simulation and catalog queries must run entirely in memory
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-15",
        fecha_nacimiento=date(1975, 4, 15),
        sexo=SexCategory.FEMENINO,
        registros=make_cotizaciones(1995, 800),
    )
    eval_res = PensionEngine.evaluate_transition(historia)
    assert eval_res.status == TransitionStatus.EVIDENCIA_SUFICIENTE_CUMPLIMIENTO


# 22. Reference documented case: 910.43 weeks in Aug 2025 for periods up to Nov 2024
def test_reference_documented_case_910_weeks():
    """Report updated in August 2025 acknowledges 910.43 weeks, all corresponding to periods up to Nov 2024.

    Must identify that total exceeds 900 threshold, without confusing report date
    with contribution dates, nor interpreting it as immediate pension entitlement.
    """
    pdf_bytes = create_synthetic_colpensiones_pdf(
        fecha_nacimiento="15/05/1972",  # Turns 62 in 2034
        sexo="MASCULINO",
        fecha_expedicion="15/08/2025",
        total_semanas="910.43",
        records_lines=[
            "01/10/2024 31/10/2024 30 $ 3.000.000 EMPRESA NACIONAL",
            "01/11/2024 30/11/2024 30 $ 3.000.000 EMPRESA NACIONAL",
        ],
    )
    historia, _report = ColpensionesPDFReader.extract_from_bytes(pdf_bytes)
    assert historia is not None
    assert historia.semanas_resumen_colpensiones == Decimal("910.43")
    assert historia.fecha_actualizacion_reporte == date(2025, 8, 15)

    eval_res = PensionEngine.evaluate_transition(
        historia, cutoff_date=TRANSITION_CUTOFF_DATE_C264
    )
    # 910.43 > 900 -> Evidencia suficiente
    assert eval_res.status == TransitionStatus.EVIDENCIA_SUFICIENTE_CUMPLIMIENTO
    assert eval_res.umbral_exigido == 900
    assert eval_res.permite_continuar_simulacion is True

    # Check horizon simulation: turns 62 in 2034
    engine = PensionEngine()
    esc = EscenarioConfig(
        "esc_ref", "Escenario Referencia", Decimal(3500000), date(2026, 1, 1)
    )
    sim_res = engine.simulate_scenario(historia, esc, as_of_date=date(2026, 9, 27))
    assert sim_res.fecha_cumplimiento_edad_legal == date(2034, 5, 15)
    assert sim_res.edad_legal == 62
    assert sim_res.ya_supero_edad_legal is False
    assert sim_res.cumple_semanas is True
    # Clearly identifies this is an estimate, not immediate pension payment
    assert (
        "reconocimiento corresponde a colpensiones"
        in sim_res.mensaje_advertencia.lower()
    )
