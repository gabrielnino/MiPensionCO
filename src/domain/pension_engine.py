"""Core Pension Engine for MiPensiónCO.

Strictly follows statutory provisions:
- Ley 100 de 1993 (Arts. 18, 21, 33, 34, 35)
- Ley 797 de 2003 (Arts. 9, 10)
- Ley 2381 de 2024 (Art. 75, Art. 76)
- Corte Constitucional C-197 de 2023 (reducción progresiva mujeres)
- Corte Constitucional C-264 de 2026 (vigencia modulada al 1 de abril de 2027)
- Corte Suprema de Justicia SL138-2024 (cómputo semanas días calendario vs mes 30 días)
- Corte Suprema de Justicia SL18546-2016 (IBL 10 años cotizaciones efectivas)
- Corte Suprema de Justicia SL3501-2022 y SL810-2023 (sin tope universal de 1.800 semanas)
- Ley 2010 de 2019 / Ley 2294 de 2023 / D. 1833 de 2016 (descuentos en salud y FSP)
"""

import calendar
from dataclasses import replace
from datetime import date, timedelta
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal
from typing import Any

from src.audit.models import (
    AuditSeverity,
    AuditStep,
    EventCode,
    ScenarioCalculationAudit,
)
from src.audit.service import AuditService
from src.domain.models import (
    AffiliationStatus,
    CotizacionRecord,
    EscenarioConfig,
    HistoriaLaboral,
    ProvenanceType,
    SexCategory,
    SimulationResult,
    TransitionEvaluation,
    TransitionStatus,
)
from src.economic.ipc import IPCFaltanteError, calculate_ipc_adjustment_factor
from src.economic.projector import EconomicProjector
from src.economic.smlmv import get_smlmv

# Official transition cutoff dates
TRANSITION_CUTOFF_DATE_ORIGINAL = date(2025, 7, 1)
TRANSITION_CUTOFF_DATE_C264 = date(2027, 4, 1)

# Schedule for women's weeks under C-197 de 2023
WOMEN_WEEKS_SCHEDULE: dict[int, int] = {
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
}


class PensionEngine:
    """Deterministic statutory pension calculator."""

    def __init__(self, projector: EconomicProjector | None = None) -> None:
        self.projector = projector or EconomicProjector()

    @staticmethod
    def get_transition_threshold(sexo: SexCategory) -> int:
        """Returns statutory threshold weeks under Ley 2381 Art. 75."""
        return 750 if sexo == SexCategory.FEMENINO else 900

    @staticmethod
    def get_legal_retirement_age(sexo: SexCategory) -> int:
        """Returns statutory retirement age under Ley 797 Art. 9."""
        return 57 if sexo == SexCategory.FEMENINO else 62

    @staticmethod
    def calculate_retirement_horizon_date(birth_date: date, sexo: SexCategory) -> date:
        """Calculates exact date when affiliate reaches ordinary legal retirement age."""
        years = PensionEngine.get_legal_retirement_age(sexo)
        try:
            return birth_date.replace(year=birth_date.year + years)
        except ValueError:
            # Handles Feb 29 on non-leap years
            return date(birth_date.year + years, 2, 28)

    @staticmethod
    def get_required_weeks_for_year(year: int, sexo: SexCategory) -> int:
        """Returns required weeks for a specific retirement year."""
        if sexo == SexCategory.MASCULINO:
            return 1300
        # For women, applies C-197 schedule
        if year <= 2025:
            return 1300
        if year >= 2036:
            return 1000
        return WOMEN_WEEKS_SCHEDULE.get(year, 1000)

    @classmethod
    def evaluate_transition(
        cls,
        historia: HistoriaLaboral,
        as_of_date: date | None = None,
        cutoff_date: date = TRANSITION_CUTOFF_DATE_C264,
        execution_id: str | None = None,
    ) -> TransitionEvaluation:
        """Evaluates whether affiliate preserves Ley 100 transition under Ley 2381 Art. 75 and C-264/2026."""
        evaluation = cls._evaluate_transition_internal(
            historia=historia, as_of_date=as_of_date, cutoff_date=cutoff_date
        )
        if execution_id:
            audit = AuditService.get_or_create_audit(execution_id)
            audit.transition_audit = {
                "rule_applied": evaluation.fuente_juridica,
                "cutoff_date": cutoff_date.isoformat(),
                "threshold_required": evaluation.umbral_exigido,
                "weeks_at_cutoff": str(evaluation.semanas_acreditadas_al_corte),
                "status": evaluation.status.value,
                "permits_continuation": evaluation.permite_continuar_simulacion,
                "explanation": evaluation.explicacion,
            }
        return evaluation

    @classmethod
    def _evaluate_transition_internal(
        cls,
        historia: HistoriaLaboral,
        as_of_date: date | None = None,
        cutoff_date: date = TRANSITION_CUTOFF_DATE_C264,
    ) -> TransitionEvaluation:
        if historia.es_caso_especial:
            return TransitionEvaluation(
                status=TransitionStatus.CASO_JURIDICO_ESPECIAL,
                umbral_exigido=0,
                semanas_acreditadas_al_corte=Decimal(0),
                fecha_corte_aplicada=cutoff_date,
                fuente_juridica="Estatuto Especial / Ley 100 Art. 36 / Decreto 2090/2003",
                explicacion=f"Caso jurídico especial identificado: {historia.detalle_caso_especial}. Requiere trámite específico fuera del simulador ordinario.",
                permite_continuar_simulacion=False,
            )

        if historia.estado_afiliacion == AffiliationStatus.PENSIONADO:
            return TransitionEvaluation(
                status=TransitionStatus.AFILIACION_FUERA_DE_ALCANCE,
                umbral_exigido=0,
                semanas_acreditadas_al_corte=Decimal(0),
                fecha_corte_aplicada=cutoff_date,
                fuente_juridica="Ley 100 de 1993",
                explicacion="La persona ya ostenta la calidad de pensionada. Solicitudes de reliquidación escapan al alcance de este simulador.",
                permite_continuar_simulacion=False,
            )

        if historia.sexo is None:
            return TransitionEvaluation(
                status=TransitionStatus.INFORMACION_INSUFICIENTE,
                umbral_exigido=750,
                semanas_acreditadas_al_corte=Decimal(0),
                fecha_corte_aplicada=cutoff_date,
                fuente_juridica="Ley 2381 de 2024, Art. 75",
                explicacion="No se ha indicado el sexo/categoría para determinar el umbral (750 semanas mujeres / 900 semanas hombres).",
                permite_continuar_simulacion=False,
            )

        umbral = cls.get_transition_threshold(historia.sexo)

        # Compute accredited weeks up to cutoff date
        # Finding 2.4 fix: Cap each period's credit to min(dias_cotizados, span_days)
        accredited_days_to_cutoff: set[date] = set()
        for r in historia.registros:
            if r.periodo_inicio <= cutoff_date:
                p_end = min(r.periodo_fin, cutoff_date)
                span_days = (p_end - r.periodo_inicio).days + 1
                if span_days > 0 and r.dias_cotizados > 0:
                    effective_days = min(r.dias_cotizados, span_days)
                    for offset in range(effective_days):
                        accredited_days_to_cutoff.add(
                            r.periodo_inicio + timedelta(days=offset)
                        )

        # Convert unique calendar days to weeks (7 days = 1 week per SL138-2024)
        semanas_al_corte = (
            Decimal(len(accredited_days_to_cutoff)) / Decimal(7)
        ).quantize(Decimal("0.01"), rounding=ROUND_FLOOR)

        latest_record_date = (
            max([r.periodo_fin for r in historia.registros])
            if historia.registros
            else None
        )
        report_date = (
            historia.fecha_actualizacion_reporte
            or historia.fecha_expedicion_reporte
            or latest_record_date
        )

        # Finding 2.5 fix: A summary issued after the cutoff date without itemized records
        # cannot prove how many weeks occurred prior to cutoff date
        if historia.semanas_resumen_colpensiones > Decimal(0):
            if report_date and report_date <= cutoff_date:
                # Certified before or on cutoff -> all recognized weeks necessarily occurred prior to cutoff
                semanas_al_corte = max(
                    semanas_al_corte, historia.semanas_resumen_colpensiones
                )
            elif not historia.registros and report_date and report_date > cutoff_date:
                # Report updated after cutoff without period records -> cannot certify transition threshold
                return TransitionEvaluation(
                    status=TransitionStatus.INFORMACION_INSUFICIENTE,
                    umbral_exigido=umbral,
                    semanas_acreditadas_al_corte=Decimal(0),
                    fecha_corte_aplicada=cutoff_date,
                    fuente_juridica="Ley 2381 de 2024, Art. 75",
                    explicacion=(
                        f"El reporte presenta {historia.semanas_resumen_colpensiones} semanas en resumen con fecha posterior al corte ({report_date.isoformat()}), "
                        f"pero no incluye el detalle de períodos cotizados para verificar cuántas semanas corresponden al período anterior al {cutoff_date.isoformat()}."
                    ),
                    permite_continuar_simulacion=False,
                )

        # Evaluation rules
        if semanas_al_corte >= Decimal(umbral):
            return TransitionEvaluation(
                status=TransitionStatus.EVIDENCIA_SUFICIENTE_CUMPLIMIENTO,
                umbral_exigido=umbral,
                semanas_acreditadas_al_corte=semanas_al_corte,
                fecha_corte_aplicada=cutoff_date,
                fuente_juridica="Ley 2381 de 2024, Art. 75 & Sentencia C-264 de 2026",
                explicacion=(
                    f"Acredita {semanas_al_corte} semanas cotizadas con anterioridad al corte de {cutoff_date.isoformat()}, "
                    f"superando el umbral legal exigido de {umbral} semanas ({'mujeres' if historia.sexo == SexCategory.FEMENINO else 'hombres'}). "
                    "Conserva la aplicación íntegra del régimen de la Ley 100 de 1993."
                ),
                permite_continuar_simulacion=True,
            )

        # If less than threshold, check if there are unknown/missing periods
        if historia.periodos_desconocidos_o_faltantes:
            return TransitionEvaluation(
                status=TransitionStatus.INFORMACION_INSUFICIENTE,
                umbral_exigido=umbral,
                semanas_acreditadas_al_corte=semanas_al_corte,
                fecha_corte_aplicada=cutoff_date,
                fuente_juridica="Ley 2381 de 2024, Art. 75",
                explicacion=(
                    f"Registra {semanas_al_corte} semanas antes de {cutoff_date.isoformat()}, valor inferior a {umbral}. "
                    "Sin embargo, existen períodos no certificados o información faltante, por lo cual no se puede descartar documentalmente la transición."
                ),
                permite_continuar_simulacion=False,
            )

        # If cutoff date is in the future relative to evaluation reference date
        today = as_of_date or date(2026, 9, 27)
        if cutoff_date > today:
            return TransitionEvaluation(
                status=TransitionStatus.EVALUACION_NO_DEFINITIVA_FECHA_CORTE_FUTURA,
                umbral_exigido=umbral,
                semanas_acreditadas_al_corte=semanas_al_corte,
                fecha_corte_aplicada=cutoff_date,
                fuente_juridica="Ley 2381 de 2024, Art. 75 & C-264 de 2026",
                explicacion=(
                    f"Registra {semanas_al_corte} semanas acreditadas. La fecha de corte aplicable ({cutoff_date.isoformat()}) "
                    f"es futura respecto a la fecha actual ({today.isoformat()}). Las semanas proyectadas a futuro no equivalen a semanas acreditadas."
                ),
                permite_continuar_simulacion=False,
            )

        # Complete information, past cutoff, strictly below threshold
        return TransitionEvaluation(
            status=TransitionStatus.NO_CUMPLE_UMBRAL_CORTE,
            umbral_exigido=umbral,
            semanas_acreditadas_al_corte=semanas_al_corte,
            fecha_corte_aplicada=cutoff_date,
            fuente_juridica="Ley 2381 de 2024, Art. 75",
            explicacion=(
                f"Acredita {semanas_al_corte} semanas frente a las {umbral} semanas exigidas al corte de {cutoff_date.isoformat()}. "
                "Con la información completa reportada, no cumple el umbral para conservar el régimen de transición de la Ley 100 de 1993."
            ),
            permite_continuar_simulacion=False,
        )

    @classmethod
    def clip_records_to_horizon(
        cls, registros: list[CotizacionRecord], horizon_date: date
    ) -> list[CotizacionRecord]:
        """Clips contribution records strictly up to the horizon date (Finding F).

        - Fully pre-horizon records (periodo_fin <= horizon_date) are kept intact.
        - Fully post-horizon records (periodo_inicio > horizon_date) are excluded.
        - Straddling records (periodo_inicio <= horizon_date < periodo_fin) are prorated.
        """
        clipped: list[CotizacionRecord] = []
        for r in registros:
            if r.excluido_del_calculo:
                continue
            if r.periodo_inicio > horizon_date:
                continue
            if r.periodo_fin <= horizon_date:
                clipped.append(r)
            else:
                # Straddling record: prorate days and IBC up to horizon_date
                clipped_span = (horizon_date - r.periodo_inicio).days + 1
                total_span = max(1, (r.periodo_fin - r.periodo_inicio).days + 1)
                prorata = Decimal(clipped_span) / Decimal(total_span)
                clipped_dias = min(r.dias_cotizados, clipped_span)
                clipped_ibc = (r.ibc * prorata).quantize(
                    Decimal(1), rounding=ROUND_HALF_UP
                )
                clipped.append(
                    CotizacionRecord(
                        periodo_inicio=r.periodo_inicio,
                        periodo_fin=horizon_date,
                        dias_reportados=clipped_dias,
                        dias_cotizados=clipped_dias,
                        ibc=clipped_ibc,
                        aportante=r.aportante,
                        nit=r.nit,
                        novedad=r.novedad,
                        observaciones=f"{r.observaciones} [Ajustado a horizonte {horizon_date.isoformat()}]",
                        fecha_pago=r.fecha_pago,
                        origen=r.origen,
                        pagina=r.pagina,
                        fila=r.fila,
                        dias_pendientes_validacion=r.dias_pendientes_validacion,
                        source_fragment_ids=r.source_fragment_ids,
                        record_id=r.record_id,
                        excluido_del_calculo=r.excluido_del_calculo,
                        motivo_exclusion=r.motivo_exclusion,
                        motivo_correccion=r.motivo_correccion,
                        estado_validacion=r.estado_validacion,
                        valor_original=r.valor_original,
                    )
                )
        return clipped

    @classmethod
    def compute_calendar_weeks(
        cls,
        registros: list[CotizacionRecord],
        horizon_date: date | None = None,
    ) -> Decimal:
        """Computes total weeks using exact calendar days (SL138-2024: 7 days = 1 week).

        Eliminates duplicate days caused by simultaneous employers.
        For partial periods, credits min(dias_cotizados, span_days).
        If horizon_date is specified, clips all records to horizon_date (Finding F).
        """
        active_records = [
            r
            for r in (
                cls.clip_records_to_horizon(registros, horizon_date)
                if horizon_date
                else registros
            )
            if not r.excluido_del_calculo
        ]
        cotized_days: set[date] = set()
        for r in active_records:
            span_days = (r.periodo_fin - r.periodo_inicio).days + 1
            if span_days <= 0 or r.dias_cotizados <= 0:
                continue
            effective_days = min(r.dias_cotizados, span_days)
            for offset in range(effective_days):
                cotized_days.add(r.periodo_inicio + timedelta(days=offset))

        return (Decimal(len(cotized_days)) / Decimal(7)).quantize(
            Decimal("0.01"), rounding=ROUND_FLOOR
        )

    @classmethod
    def consolidate_monthly_contributions(
        cls,
        registros: list[CotizacionRecord],
        horizon_date: date | None = None,
        projector: EconomicProjector | None = None,
    ) -> list[tuple[int, int, int, Decimal]]:
        """Consolidates cotizacion records into unified monthly periods (Finding 2.7 & 2.8).

        Statutory rules:
        - Ley 100 Art. 18 & D. 1833 de 2016: Simultaneous employers in the same month consolidate
          their IBCs (up to statutory cap of 25 SMLMV for that year) for at most 30 effective days.
        - Excludes records where periodo_inicio > horizon_date (Finding 2.8).
        - Multi-month continuous records are sliced into monthly periods of at most 30 days each.

        Returns:
            List of (year, month, effective_days, consolidated_ibc) ordered descending by (year, month).
        """
        proj = projector or EconomicProjector()
        month_buckets: dict[tuple[int, int], list[tuple[int, Decimal]]] = {}

        for r in registros:
            if r.excluido_del_calculo:
                continue
            # Finding 2.8: exclude contributions starting strictly after the horizon date
            if horizon_date and r.periodo_inicio > horizon_date:
                continue

            r_end = min(r.periodo_fin, horizon_date) if horizon_date else r.periodo_fin
            r_start = r.periodo_inicio
            if r_start > r_end or r.dias_cotizados <= 0:
                continue

            # Calculate total months spanned by this record
            months_count = (
                (r_end.year - r_start.year) * 12 + (r_end.month - r_start.month) + 1
            )

            if months_count == 1:
                key = (r_end.year, r_end.month)
                span_days = (r_end - r_start).days + 1
                eff_days = min(30, min(r.dias_cotizados, span_days))
                if key not in month_buckets:
                    month_buckets[key] = []
                month_buckets[key].append((eff_days, r.ibc))
            else:
                # Decompose multi-month record
                cur_y, cur_m = r_start.year, r_start.month
                days_per_month = min(30, max(1, r.dias_cotizados // months_count))
                while (cur_y < r_end.year) or (
                    cur_y == r_end.year and cur_m <= r_end.month
                ):
                    key = (cur_y, cur_m)
                    m_start = max(r_start, date(cur_y, cur_m, 1))
                    m_end = min(
                        r_end, date(cur_y, cur_m, calendar.monthrange(cur_y, cur_m)[1])
                    )
                    m_span = (m_end - m_start).days + 1
                    eff_m_days = min(30, min(days_per_month, m_span))
                    if key not in month_buckets:
                        month_buckets[key] = []
                    month_buckets[key].append((eff_m_days, r.ibc))

                    if cur_m == 12:
                        cur_y += 1
                        cur_m = 1
                    else:
                        cur_m += 1

        consolidated: list[tuple[int, int, int, Decimal]] = []
        for key in sorted(month_buckets.keys(), reverse=True):
            y, m = key
            entries = month_buckets[key]
            # Cap monthly effective days at 30 days
            month_days = min(30, sum(d for d, _ in entries))
            # Reference SMLMV for the 25 SMLMV ceiling
            try:
                smlmv_ref = get_smlmv(y).monthly_amount
            except ValueError:
                smlmv_ref = proj.get_projected_smlmv(y)

            max_ibc_month = smlmv_ref * Decimal(25)
            total_ibc_month = min(
                max_ibc_month, sum((ibc for _, ibc in entries), Decimal(0))
            )
            if month_days > 0 and total_ibc_month > Decimal(0):
                consolidated.append((y, m, month_days, total_ibc_month))

        return consolidated

    @classmethod
    def build_monthly_cotizaciones(
        cls,
        registros: list[CotizacionRecord],
        horizon_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Convenience method returning list of monthly cotizaciones dictionaries."""
        consolidated = cls.consolidate_monthly_contributions(registros, horizon_date)
        return [
            {"year": y, "month": m, "days": d, "ibc": ibc}
            for y, m, d, ibc in consolidated
        ]

    def calculate_ibl(
        self,
        historia: HistoriaLaboral,
        target_year: int,
        target_month: int,
        assumed_inflation: Decimal = Decimal("0.04"),
        records: list[CotizacionRecord] | None = None,
        horizon_date: date | None = None,
        return_details: bool = False,
        projector: EconomicProjector | None = None,
    ) -> Any:
        """Calculates IBL comparing 10-year effective cotizaciones vs lifetime average.

        Under SL18546-2016, 10 years means 3,650 days of effective cotizaciones (not calendar months).
        Under Ley 100 Art. 21, lifetime average is only accessible if total accredited weeks >= 1,250.
        Simultaneous employers are consolidated per Finding 2.7.
        Post-horizon records are excluded per Finding 2.8.
        """
        active_records = records if records is not None else historia.registros
        if not active_records:
            return (
                (None, None, "SIN_REGISTROS", Decimal(0), [])
                if return_details
                else (None, None, "SIN_REGISTROS", Decimal(0))
            )

        # Consolidate records by month
        monthly_contributions = self.consolidate_monthly_contributions(
            active_records,
            horizon_date=horizon_date,
            projector=projector or self.projector,
        )
        if not monthly_contributions:
            return (
                (None, None, "SIN_REGISTROS", Decimal(0), [])
                if return_details
                else (None, None, "SIN_REGISTROS", Decimal(0))
            )

        # 1. 10 years of effective contributions (3,650 days)
        effective_days_needed = 3650
        accumulated_days_10y = 0
        weighted_ibc_sum_10y = Decimal(0)
        effective_details: list[dict[str, Any]] = []

        for y, m, days_in_month, ibc_month in monthly_contributions:
            dias_a_tomar = min(
                days_in_month, effective_days_needed - accumulated_days_10y
            )
            factor_ipc = calculate_ipc_adjustment_factor(
                initial_year=y,
                initial_month=m,
                target_year=target_year,
                target_month=target_month,
                assumed_annual_inflation=assumed_inflation,
            )
            ibc_actualizado = (ibc_month * factor_ipc).quantize(
                Decimal(1), rounding=ROUND_HALF_UP
            )
            weighted_ibc_sum_10y += ibc_actualizado * Decimal(dias_a_tomar)
            accumulated_days_10y += dias_a_tomar

            effective_details.append(
                {
                    "ano": y,
                    "mes": m,
                    "dias_efectivos": dias_a_tomar,
                    "ibc_nominal": str(ibc_month),
                    "factor_ipc": f"{factor_ipc:.4f}",
                    "ibc_actualizado": str(ibc_actualizado),
                }
            )

            if accumulated_days_10y >= effective_days_needed:
                break

        ibl_10y = (
            (weighted_ibc_sum_10y / Decimal(accumulated_days_10y)).quantize(
                Decimal(1), rounding=ROUND_HALF_UP
            )
            if accumulated_days_10y > 0
            else None
        )

        # 2. Lifetime average (toda la vida laboral)
        total_weeks = self.compute_calendar_weeks(active_records)
        total_days_all = 0
        weighted_ibc_sum_all = Decimal(0)

        for y, m, days_in_month, ibc_month in monthly_contributions:
            factor_ipc = calculate_ipc_adjustment_factor(
                initial_year=y,
                initial_month=m,
                target_year=target_year,
                target_month=target_month,
                assumed_annual_inflation=assumed_inflation,
            )
            weighted_ibc_sum_all += (ibc_month * factor_ipc) * Decimal(days_in_month)
            total_days_all += days_in_month

        ibl_all = (
            (weighted_ibc_sum_all / Decimal(total_days_all)).quantize(
                Decimal(1), rounding=ROUND_HALF_UP
            )
            if total_days_all > 0
            else None
        )

        # Compare and select
        # Lifetime is eligible only if >= 1,250 weeks and if higher than 10y
        if (
            total_weeks >= Decimal(1250)
            and ibl_all is not None
            and ibl_10y is not None
            and ibl_all > ibl_10y
        ):
            metodo = "TODA_LA_VIDA_SUPERIOR"
            final_ibl = ibl_all
        elif ibl_10y is not None:
            metodo = "ULTIMOS_10_ANOS_EFECTIVOS"
            final_ibl = ibl_10y
        elif ibl_all is not None:
            metodo = "TOTAL_DISPONIBLE"
            final_ibl = ibl_all
        else:
            metodo = "SIN_REGISTROS"
            final_ibl = Decimal(0)

        if return_details:
            return ibl_10y, ibl_all, metodo, final_ibl, effective_details
        return ibl_10y, ibl_all, metodo, final_ibl

        return None, None, "SIN_REGISTROS", Decimal(0)

    def calculate_replacement_rate(
        self,
        ibl: Decimal,
        smlmv_ref: Decimal,
        total_weeks: Decimal,
        required_weeks: int,
    ) -> tuple[Decimal, Decimal, Decimal, int, Decimal, Decimal]:
        """Calculates replacement rate under Ley 797 Art. 10 & SL810-2023.

        Returns:
            (s_factor, tasa_inicial_pct, semanas_adicionales, bloques_completos, incremento_pct, tasa_final_pct)
        """
        # s = IBL / SMLMV
        s_factor = (ibl / smlmv_ref).quantize(Decimal("0.0001"))

        # Initial formula: r = 65.50 - 0.50 * s
        tasa_inicial = Decimal("65.50") - (Decimal("0.50") * s_factor)
        # Bounded between 0 and 65.5
        tasa_inicial = max(Decimal(0), min(Decimal("65.50"), tasa_inicial)).quantize(
            Decimal("0.01")
        )

        # Weeks above minimum required
        semanas_adicionales = max(Decimal(0), total_weeks - Decimal(required_weeks))
        bloques_50 = int(semanas_adicionales // Decimal(50))
        incremento = (Decimal(bloques_50) * Decimal("1.50")).quantize(Decimal("0.01"))

        # SL3501-2022 and SL810-2023: weeks beyond 1,800 can be counted to reach up to 80%
        tasa_final = min(Decimal("80.00"), tasa_inicial + incremento).quantize(
            Decimal("0.01")
        )

        return (
            s_factor,
            tasa_inicial,
            semanas_adicionales,
            bloques_50,
            incremento,
            tasa_final,
        )

    @staticmethod
    def calculate_deductions(
        mesada_bruta: Decimal, smlmv_ref: Decimal
    ) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal]:
        """Calculates mandatory legal deductions: Salud and FSP subsistencia.

        Returns:
            (salud_pct, salud_monto, fsp_pct, fsp_monto, valor_despues_descuentos)
        """
        multiples = mesada_bruta / smlmv_ref

        # Health contribution
        if multiples <= Decimal("1.0001"):
            salud_pct = Decimal("4.00")
        elif multiples <= Decimal("3.0001"):
            salud_pct = Decimal("10.00")
        else:
            salud_pct = Decimal("12.00")

        salud_monto = (mesada_bruta * (salud_pct / Decimal(100))).quantize(
            Decimal(1), rounding=ROUND_HALF_UP
        )

        # Solidarity fund (Subcuenta de subsistencia)
        if multiples > Decimal("20.00"):
            fsp_pct = Decimal("2.00")
        elif multiples > Decimal("10.00"):
            fsp_pct = Decimal("1.00")
        else:
            fsp_pct = Decimal("0.00")

        fsp_monto = (mesada_bruta * (fsp_pct / Decimal(100))).quantize(
            Decimal(1), rounding=ROUND_HALF_UP
        )

        total_deductions = salud_monto + fsp_monto
        valor_despues = mesada_bruta - total_deductions

        return salud_pct, salud_monto, fsp_pct, fsp_monto, valor_despues

    @staticmethod
    def additional_declared_weeks(
        documentary_records: list[CotizacionRecord],
        declared_records: list[CotizacionRecord],
    ) -> tuple[Decimal, bool]:
        """Count new declared coverage without certifying overlapping contributions.

        SL138-2024: simultaneous employers cannot create additional calendar days.
        An overlap may be a correction or a separate employer: until reviewed it
        must not inflate either weeks or IBL. Partial coverage has no known dates;
        overlapping partial records therefore remain pending rather than being
        assigned invented coverage dates.
        """
        occupied_days: set[date] = set()
        for record in documentary_records:
            occupied_days.update(
                record.periodo_inicio + timedelta(days=offset)
                for offset in range(
                    max(0, (record.periodo_fin - record.periodo_inicio).days + 1)
                )
            )
        additional_days = 0
        has_overlap = False
        # Stable ordering makes ambiguous partial coverage independent of input order.
        for record in sorted(
            declared_records, key=lambda item: (item.periodo_inicio, item.periodo_fin)
        ):
            interval_days = {
                record.periodo_inicio + timedelta(days=offset)
                for offset in range(
                    max(0, (record.periodo_fin - record.periodo_inicio).days + 1)
                )
            }
            overlaps = bool(interval_days & occupied_days)
            has_overlap = has_overlap or overlaps
            if record.dias_cotizados >= len(interval_days):
                additional_days += len(interval_days - occupied_days)
            elif not overlaps:
                additional_days += max(0, record.dias_cotizados)
            occupied_days.update(interval_days)
        weeks = (Decimal(additional_days) / Decimal(7)).quantize(
            Decimal("0.01"), rounding=ROUND_FLOOR
        )
        return weeks, has_overlap

    def simulate_scenario(
        self,
        historia: HistoriaLaboral,
        escenario: EscenarioConfig,
        as_of_date: date | None = None,
        execution_id: str | None = None,
    ) -> SimulationResult:
        """Executes complete deterministic simulation terminating strictly at legal retirement age.

        Incorporates fixes for:
        - Finding 2.2: Generates hypothetical monthly future contributions reflecting escenario.ibc_futuro_inicial.
        - Finding 2.3: Blocks mesada (None) when no salary/IBC data exists in history.
        - Finding 2.8: Strictly excludes post-horizon contributions from pension determination.
        """
        today = as_of_date or date(2026, 9, 27)
        # Each scenario owns its economic assumptions; never mutate the shared engine.
        scenario_projector = EconomicProjector(
            replace(
                self.projector.assumptions,
                assumed_annual_inflation=escenario.supuesto_inflacion,
                assumed_annual_smlmv_growth=escenario.supuesto_crecimiento_smlmv,
            )
        )

        if historia.fecha_nacimiento is None or historia.sexo is None:
            raise ValueError(
                "La fecha de nacimiento y el sexo son obligatorios para calcular el horizonte legal."
            )

        horizon_date = self.calculate_retirement_horizon_date(
            historia.fecha_nacimiento, historia.sexo
        )
        legal_age = self.get_legal_retirement_age(historia.sexo)
        required_weeks = self.get_required_weeks_for_year(
            horizon_date.year, historia.sexo
        )

        ya_supero_edad = today >= horizon_date

        # 1. Accredited documentary and calendar weeks (filtered to horizon_date)
        historical_records_to_horizon = self.clip_records_to_horizon(
            historia.registros, horizon_date
        )
        doc_records = [
            r
            for r in historical_records_to_horizon
            if r.origen != ProvenanceType.DECLARACION_USUARIO
        ]
        decl_records = [
            r
            for r in historical_records_to_horizon
            if r.origen == ProvenanceType.DECLARACION_USUARIO
        ]

        semanas_doc = (
            historia.semanas_resumen_colpensiones
            if historia.semanas_resumen_colpensiones > Decimal(0)
            else self.compute_calendar_weeks(doc_records)
        )
        semanas_declaradas, has_declared_overlap = self.additional_declared_weeks(
            doc_records, decl_records
        )
        semanas_cal = self.compute_calendar_weeks(historia.registros)
        diferencia_cal = (semanas_cal - (semanas_doc + semanas_declaradas)).quantize(
            Decimal("0.01")
        )

        # Evaluate material discrepancy
        # Check if discrepancy alters eligibility threshold
        semanas_base_total = semanas_doc + semanas_declaradas
        cambia_elegibilidad = (
            semanas_base_total < Decimal(required_weeks) <= semanas_cal
        ) or (semanas_cal < Decimal(required_weeks) <= semanas_base_total)

        # Check if discrepancy alters 50-week blocks relative to applicable legal requirement
        # Ley 797 de 2003, Art. 10: additional blocks beyond required_weeks
        bloques_doc = max(0, int((semanas_base_total - Decimal(required_weeks)) // 50))
        bloques_cal = max(0, int((semanas_cal - Decimal(required_weeks)) // 50))
        cambia_bloque = bloques_doc != bloques_cal

        requiere_revision_discrepancia = bool(
            cambia_elegibilidad
            or (cambia_bloque and abs(diferencia_cal) >= Decimal("0.01"))
        )

        # Base accredited weeks: Use proven recognized summary if present, else recalculation
        base_weeks = (
            semanas_doc
            if historia.semanas_resumen_colpensiones > Decimal(0)
            else self.compute_calendar_weeks(doc_records)
        )

        # 2. Future contributions strictly after today / evaluation date
        # NEVER invent past contributions between last contribution and evaluation date!
        projected_future_records: list[CotizacionRecord] = []
        semanas_proyectadas = Decimal(0)

        # Merge overlapping pause intervals (Finding C)
        merged_pauses: list[tuple[date, date]] = []
        if escenario.periodos_sin_aporte:
            sorted_p = sorted(escenario.periodos_sin_aporte, key=lambda x: x[0])
            merged_pauses = [sorted_p[0]]
            for cur_p in sorted_p[1:]:
                last_s, last_e = merged_pauses[-1]
                if cur_p[0] <= last_e + timedelta(days=1):
                    merged_pauses[-1] = (last_s, max(last_e, cur_p[1]))
                else:
                    merged_pauses.append(cur_p)

        def make_span_records(
            start_date: date,
            end_date: date,
            provenance: ProvenanceType,
            prefix: str,
        ) -> list[CotizacionRecord]:
            res_recs: list[CotizacionRecord] = []
            if start_date >= end_date:
                return res_recs

            cur_y, cur_m = start_date.year, start_date.month
            while (cur_y < end_date.year) or (
                cur_y == end_date.year and cur_m <= end_date.month
            ):
                m_start = max(start_date, date(cur_y, cur_m, 1))
                m_last_day = calendar.monthrange(cur_y, cur_m)[1]
                m_end = min(
                    end_date - timedelta(days=1),
                    date(cur_y, cur_m, m_last_day),
                )

                if m_start <= m_end:
                    span_cal_days = (m_end - m_start).days + 1
                    full_month_days = m_last_day

                    # Deduct ONLY days that intersect with pauses (Finding C)
                    paused_days = 0
                    for p_start, p_end in merged_pauses:
                        inter_s = max(m_start, p_start)
                        inter_e = min(m_end, p_end)
                        if inter_s <= inter_e:
                            paused_days += (inter_e - inter_s).days + 1

                    active_cal_days = max(0, span_cal_days - paused_days)

                    if active_cal_days > 0:
                        # Finding E: Separate calendar coverage days from 30-day billing convention
                        billing_days = min(
                            30,
                            round(
                                Decimal(active_cal_days)
                                * Decimal(30)
                                / Decimal(full_month_days)
                            ),
                        )

                        # Calculate nominal IBC for projected year
                        years_diff = max(0, cur_y - escenario.fecha_inicio_ibc.year)
                        growth_factor = (
                            Decimal(1) + escenario.crecimiento_anual_nominal
                        ) ** Decimal(years_diff)
                        annual_ibc = (
                            escenario.ibc_futuro_inicial * growth_factor
                        ).quantize(Decimal(1), rounding=ROUND_HALF_UP)

                        # Bound between 1 and 25 SMLMV
                        smlmv_proj = scenario_projector.get_projected_smlmv(cur_y)
                        annual_ibc = max(
                            smlmv_proj,
                            min(smlmv_proj * Decimal(25), annual_ibc),
                        )

                        # Finding C: Weight income proportionally by active days
                        weighted_ibc = (
                            annual_ibc
                            * Decimal(active_cal_days)
                            / Decimal(full_month_days)
                        ).quantize(Decimal(1), rounding=ROUND_HALF_UP)

                        res_recs.append(
                            CotizacionRecord(
                                periodo_inicio=m_start,
                                periodo_fin=m_end,
                                dias_reportados=billing_days,
                                dias_cotizados=active_cal_days,
                                ibc=weighted_ibc,
                                aportante=f"{prefix}: {escenario.nombre}",
                                origen=provenance,
                            )
                        )

                if cur_m == 12:
                    cur_y += 1
                    cur_m = 1
                else:
                    cur_m += 1

            return res_recs

        if ya_supero_edad:
            # Finding F: For past horizon, weeks at retirement age strictly exclude post-horizon
            has_post_horizon_records = any(
                r.periodo_fin > horizon_date for r in historia.registros
            )
            if has_post_horizon_records:
                semanas_totales = self.compute_calendar_weeks(
                    historical_records_to_horizon
                )
            else:
                semanas_totales = base_weeks + semanas_declaradas
            semanas_proyectadas = Decimal(0)
        else:
            # Strictly future projected contributions
            fut_start = max(
                today + timedelta(days=1),
                escenario.fecha_inicio_ibc,
            )
            projected_future_records = make_span_records(
                fut_start,
                horizon_date,
                ProvenanceType.SUPUESTO,
                "PROYECCIÓN",
            )
            total_proj_days = sum(r.dias_cotizados for r in projected_future_records)
            semanas_proyectadas = (Decimal(total_proj_days) / Decimal(7)).quantize(
                Decimal("0.01"), rounding=ROUND_FLOOR
            )

            semanas_totales = (
                base_weeks + semanas_declaradas + semanas_proyectadas
            ).quantize(Decimal("0.01"))

        cumple_semanas = semanas_totales >= Decimal(required_weeks)

        # Single decision of enablement across all engine paths:
        # Liquidation is enabled ONLY if affiliate meets required weeks, has no unresolved documentary discrepancy,
        # and has no declared unknown/missing periods.
        es_liquidable = (
            cumple_semanas
            and not requiere_revision_discrepancia
            and not historia.periodos_desconocidos_o_faltantes
            and not has_declared_overlap
        )

        deficit = max(Decimal(0), Decimal(required_weeks) - semanas_totales).quantize(
            Decimal("0.01")
        )
        excedente = max(Decimal(0), semanas_totales - Decimal(required_weeks)).quantize(
            Decimal("0.01")
        )

        smlmv_ref = scenario_projector.get_projected_smlmv(horizon_date.year)

        # Step breakdown narrative
        desglose: list[str] = [
            f"Horizonte ordinario: {horizon_date.isoformat()} (cumplimiento de {legal_age} años).",
            f"Requisito legal aplicable ({horizon_date.year}): {required_weeks} semanas.",
            f"Semanas reconocidas documentales: {semanas_doc}. Semanas declaradas por el usuario: {semanas_declaradas}. Semanas recalculadas por días calendario: {semanas_cal}.",
        ]

        if ya_supero_edad:
            desglose.append(
                "La persona ya superó la edad legal ordinaria. No se proyectan aportes futuros hacia una fecha pasada."
            )
        else:
            desglose.append(
                f"Semanas proyectadas hasta la edad legal: {semanas_proyectadas} (con IBC proyectado ${escenario.ibc_futuro_inicial:,.0f} COP)."
            )

        desglose.append(f"Total semanas a la edad legal: {semanas_totales}.")

        scenario_inputs: dict[str, Any] = {
            "ibc_futuro": str(escenario.ibc_futuro_inicial),
            "ibc_futuro_nominal": str(escenario.ibc_futuro_inicial),
            "fecha_inicio": escenario.fecha_inicio_ibc.isoformat(),
            "fecha_inicio_ibc": escenario.fecha_inicio_ibc.isoformat(),
            "crecimiento": str(escenario.crecimiento_anual_nominal),
            "crecimiento_anual_nominal": str(escenario.crecimiento_anual_nominal),
            "semanas_proyectadas": str(semanas_proyectadas),
            "motivo_terminacion_o_pausa_aportes": (
                "Superó edad legal ordinaria previa a la simulación; no se proyectan aportes hacia el pasado."
                if ya_supero_edad
                else "Llegada a la fecha de cumplimiento de edad legal ordinaria (horizonte fijo de retiro)."
            ),
            "supuestos_economicos": {
                "inflacion_anual_proyeccion": str(escenario.supuesto_inflacion),
                "crecimiento_anual_smlmv": str(escenario.supuesto_crecimiento_smlmv),
            },
        }

        # If not enabled for liquidation (deficit, discrepancy, or unknown periods):
        if not es_liquidable:
            if has_declared_overlap:
                advertencia = (
                    "Superposición de períodos declarados con registros existentes. "
                    "Solo se añaden días nuevos identificables; revise si se trata de "
                    "una corrección o de otro empleador antes de liquidar el IBL."
                )
                desglose.append(advertencia)
                blocking_code = "SUPERPOSICION_DECLARADA_PENDIENTE"
                blocking_limit = "BLOQUEADO_POR_SUPERPOSICION"
            elif requiere_revision_discrepancia:
                advertencia = (
                    f"DISCREPANCIA DOCUMENTAL: El resumen de semanas ({semanas_doc}) difiere del recálculo de períodos ({semanas_cal}) "
                    f"con información salarial insuficiente para liquidar. "
                    f"La mesada no puede liquidarse automáticamente mientras exista una discrepancia pendiente de revisión documental."
                )
                desglose.append(advertencia)
                blocking_code = "DISCREPANCIA_DOCUMENTAL_SEMANAS"
                blocking_limit = "BLOQUEADO_POR_DISCREPANCIA"
            elif historia.periodos_desconocidos_o_faltantes:
                advertencia = (
                    "Se declararon períodos faltantes o desconocidos en la historia laboral. "
                    "Las conclusiones pensionales definitivas quedan bloqueadas hasta verificar los períodos pendientes."
                )
                desglose.append(advertencia)
                blocking_code = "PERIODOS_HISTORICOS_DESCONOCIDOS"
                blocking_limit = "BLOQUEADO_POR_PERIODOS_DESCONOCIDOS"
            else:
                desglose.append(
                    f"DÉFICIT PENSIONAL: Faltan {deficit} semanas para reunir el requisito legal a la edad ordinaria."
                )
                desglose.append(
                    "REGLA ESTRICTA DE PRODUCTO: No se calcula una mesada pagadera ni se proyectan aportes posteriores a la edad legal."
                )
                advertencia = "No cumple con las semanas mínimas requeridas a la edad legal ordinaria. No se reconoce mesada pensional."
                blocking_code = "DEFICIT_SEMANAS_A_LA_EDAD_LEGAL"
                blocking_limit = "NINGUNO"

            if execution_id:
                AuditService.add_scenario_audit(
                    execution_id,
                    ScenarioCalculationAudit(
                        scenario_id=escenario.escenario_id,
                        scenario_name=escenario.nombre,
                        fixed_horizon_date=horizon_date.isoformat(),
                        legal_retirement_age=legal_age,
                        inputs=scenario_inputs,
                        generated_future_periods_count=len(projected_future_records),
                        weeks_breakdown={
                            "documentales": str(semanas_doc),
                            "declaradas_adicionales": str(semanas_declaradas),
                            "declaradas": str(semanas_declaradas),
                            "calendario": str(semanas_cal),
                            "proyectadas": str(semanas_proyectadas),
                            "totales": str(semanas_totales),
                            "exigidas": str(required_weeks),
                            "deficit": str(deficit),
                        },
                        effective_contributions_selected=[],
                        ibl_method_chosen="NO_APLICA_BLOQUEADO",
                        ibl_final=None,
                        smlmv_ref=str(smlmv_ref),
                        s_factor=None,
                        replacement_rate_initial_pct=None,
                        additional_weeks_blocks=None,
                        replacement_rate_final_pct=None,
                        gross_pension=None,
                        limit_applied=blocking_limit,
                        health_discount_pct=None,
                        health_discount_amount=None,
                        fsp_discount_pct=None,
                        fsp_discount_amount=None,
                        net_pension_after_discounts=None,
                        real_purchasing_power_cop=None,
                        smlmv_multiples=None,
                        is_blocked=True,
                        blocking_reason=blocking_code,
                        step_by_step_operations=desglose,
                        data_version_used=f"Rev {historia.revision_version} ({historia.revision_id})",
                        provenance_counts={
                            "PDF": sum(
                                1
                                for r in historia.registros
                                if r.origen == ProvenanceType.PDF
                                and not r.excluido_del_calculo
                            ),
                            "DECLARACION_USUARIO": sum(
                                1
                                for r in historia.registros
                                if r.origen == ProvenanceType.DECLARACION_USUARIO
                                and not r.excluido_del_calculo
                            ),
                            "CORRECCION_MANUAL": sum(
                                1
                                for r in historia.registros
                                if r.origen == ProvenanceType.CORRECCION_MANUAL
                                and not r.excluido_del_calculo
                            ),
                            "EXCLUIDO": sum(
                                1 for r in historia.registros if r.excluido_del_calculo
                            ),
                        },
                    ),
                )
                AuditService.log_technical(
                    execution_id,
                    AuditStep.EVALUACION_JURIDICA,
                    "PensionEngine",
                    0.0,
                    AuditSeverity.INFO,
                    EventCode.DEFICIT_SEMANAS_HORIZONTE
                    if not cumple_semanas
                    else EventCode.DISCREPANCIA_RESUMEN_DETALLE,
                    "BLOQUEADO",
                    blocking_code,
                    "Revisar evidencia documental o completar requisitos",
                )

            return SimulationResult(
                escenario_id=escenario.escenario_id,
                escenario_nombre=escenario.nombre,
                fecha_cumplimiento_edad_legal=horizon_date,
                edad_legal=legal_age,
                ya_supero_edad_legal=ya_supero_edad,
                semanas_exigidas=required_weeks,
                semanas_acreditadas_documentales=semanas_doc,
                semanas_recalculadas_calendario=semanas_cal,
                diferencia_semanas_recalculadas=diferencia_cal,
                semanas_futuras_proyectadas=semanas_proyectadas,
                semanas_totales_a_la_edad=semanas_totales,
                cumple_semanas=cumple_semanas,
                deficit_semanas=deficit,
                excedente_semanas=excedente if cumple_semanas else Decimal(0),
                ibl_ultimos_10_anos=None,
                ibl_toda_la_vida=None,
                metodo_ibl_seleccionado=None,
                ibl_final=None,
                smlmv_referencia_retiro=smlmv_ref,
                s_factor=None,
                tasa_reemplazo_inicial_pct=None,
                semanas_adicionales_computables=None,
                bloques_completos_50_semanas=None,
                incremento_tasa_pct=None,
                tasa_reemplazo_final_pct=None,
                mesada_bruta=None,
                limite_aplicado=blocking_limit,
                descuento_salud_pct=None,
                descuento_salud_monto=None,
                descuento_fsp_pct=None,
                descuento_fsp_monto=None,
                valor_despues_descuentos=None,
                valor_real_poder_adquisitivo=None,
                equivalente_smlmv=None,
                mensaje_advertencia=advertencia,
                desglose_explicativo=desglose,
                requiere_revision_discrepancia=requiere_revision_discrepancia,
                bloqueado_por_periodo_desconocido=historia.periodos_desconocidos_o_faltantes,
            )

        # 3. Calculate IBL using historical records (including user declarations) + projected future records
        all_simulation_records = (
            historical_records_to_horizon + projected_future_records
        )

        # Finding 2.3 Fix: If there are NO salary records, block mesada with explicit warning
        has_salary_data = any(r.ibc > Decimal(0) for r in all_simulation_records)
        if not has_salary_data:
            advertencia = (
                "No existen registros de salarios o IBC en la historia laboral para calcular el IBL. "
                "La mesada no puede liquidarse sin datos salariales verificables (IBL_INSUFICIENTE_DATOS_SALARIALES)."
            )
            desglose.append(
                "BLOQUEO DE LIQUIDACIÓN: IBL_INSUFICIENTE_DATOS_SALARIALES."
            )
            desglose.append(advertencia)

            if execution_id:
                AuditService.add_scenario_audit(
                    execution_id,
                    ScenarioCalculationAudit(
                        scenario_id=escenario.escenario_id,
                        scenario_name=escenario.nombre,
                        fixed_horizon_date=horizon_date.isoformat(),
                        legal_retirement_age=legal_age,
                        inputs=scenario_inputs,
                        generated_future_periods_count=len(projected_future_records),
                        weeks_breakdown={
                            "documentales": str(semanas_doc),
                            "declaradas_adicionales": str(semanas_declaradas),
                            "calendario": str(semanas_cal),
                            "proyectadas": str(semanas_proyectadas),
                            "totales": str(semanas_totales),
                            "exigidas": str(required_weeks),
                            "deficit": str(deficit),
                        },
                        effective_contributions_selected=[],
                        ibl_method_chosen="SIN_REGISTROS_SALARIALES",
                        ibl_final=None,
                        smlmv_ref=str(smlmv_ref),
                        s_factor=None,
                        replacement_rate_initial_pct=None,
                        additional_weeks_blocks=None,
                        replacement_rate_final_pct=None,
                        gross_pension=None,
                        limit_applied="BLOQUEADO_SIN_SALARIOS",
                        health_discount_pct=None,
                        health_discount_amount=None,
                        fsp_discount_pct=None,
                        fsp_discount_amount=None,
                        net_pension_after_discounts=None,
                        real_purchasing_power_cop=None,
                        smlmv_multiples=None,
                        is_blocked=True,
                        blocking_reason="IBL_INSUFICIENTE_DATOS_SALARIALES",
                        step_by_step_operations=desglose,
                        data_version_used=f"Rev {historia.revision_version} ({historia.revision_id})",
                        provenance_counts={
                            "PDF": sum(
                                1
                                for r in historia.registros
                                if r.origen == ProvenanceType.PDF
                                and not r.excluido_del_calculo
                            ),
                            "DECLARACION_USUARIO": sum(
                                1
                                for r in historia.registros
                                if r.origen == ProvenanceType.DECLARACION_USUARIO
                                and not r.excluido_del_calculo
                            ),
                            "CORRECCION_MANUAL": sum(
                                1
                                for r in historia.registros
                                if r.origen == ProvenanceType.CORRECCION_MANUAL
                                and not r.excluido_del_calculo
                            ),
                            "EXCLUIDO": sum(
                                1 for r in historia.registros if r.excluido_del_calculo
                            ),
                        },
                    ),
                )
                AuditService.log_technical(
                    execution_id,
                    AuditStep.LIQUIDACION_PENSIONAL,
                    "PensionEngine",
                    0.0,
                    AuditSeverity.ADVERTENCIA,
                    EventCode.IBL_INSUFICIENTE_DATOS_SALARIALES,
                    "BLOQUEADO",
                    "Sin registros salariales",
                    "Ingresar manualmente cotizaciones históricas o actualizar PDF con detalle",
                )

            return SimulationResult(
                escenario_id=escenario.escenario_id,
                escenario_nombre=escenario.nombre,
                fecha_cumplimiento_edad_legal=horizon_date,
                edad_legal=legal_age,
                ya_supero_edad_legal=ya_supero_edad,
                semanas_exigidas=required_weeks,
                semanas_acreditadas_documentales=semanas_doc,
                semanas_recalculadas_calendario=semanas_cal,
                diferencia_semanas_recalculadas=diferencia_cal,
                semanas_futuras_proyectadas=semanas_proyectadas,
                semanas_totales_a_la_edad=semanas_totales,
                cumple_semanas=True,
                deficit_semanas=Decimal(0),
                excedente_semanas=excedente,
                ibl_ultimos_10_anos=None,
                ibl_toda_la_vida=None,
                metodo_ibl_seleccionado="SIN_REGISTROS",
                ibl_final=None,
                smlmv_referencia_retiro=smlmv_ref,
                s_factor=None,
                tasa_reemplazo_inicial_pct=None,
                semanas_adicionales_computables=None,
                bloques_completos_50_semanas=None,
                incremento_tasa_pct=None,
                tasa_reemplazo_final_pct=None,
                mesada_bruta=None,
                limite_aplicado="BLOQUEADO_SIN_SALARIOS",
                descuento_salud_pct=None,
                descuento_salud_monto=None,
                descuento_fsp_pct=None,
                descuento_fsp_monto=None,
                valor_despues_descuentos=None,
                valor_real_poder_adquisitivo=None,
                equivalente_smlmv=None,
                mensaje_advertencia=advertencia,
                desglose_explicativo=desglose,
                requiere_revision_discrepancia=requiere_revision_discrepancia,
            )

        # Finding I: Catch IPCFaltanteError during IBL calculation
        try:
            (
                ibl_10y,
                ibl_all,
                metodo_ibl,
                ibl_final,
                effective_selected,
            ) = self.calculate_ibl(
                historia=historia,
                target_year=horizon_date.year,
                target_month=horizon_date.month,
                assumed_inflation=escenario.supuesto_inflacion,
                records=all_simulation_records,
                horizon_date=horizon_date,
                return_details=True,
                projector=scenario_projector,
            )
        except IPCFaltanteError as exc:
            advertencia = (
                f"Cálculo bloqueado por ausencia de IPC oficial mensual: {exc}"
            )
            desglose.append(f"BLOQUEO ECONÓMICO: {exc}")
            if execution_id:
                AuditService.add_scenario_audit(
                    execution_id,
                    ScenarioCalculationAudit(
                        scenario_id=escenario.escenario_id,
                        scenario_name=escenario.nombre,
                        fixed_horizon_date=horizon_date.isoformat(),
                        legal_retirement_age=legal_age,
                        inputs=scenario_inputs,
                        generated_future_periods_count=len(projected_future_records),
                        weeks_breakdown={
                            "documentales": str(semanas_doc),
                            "declaradas_adicionales": str(semanas_declaradas),
                            "calendario": str(semanas_cal),
                            "proyectadas": str(semanas_proyectadas),
                            "totales": str(semanas_totales),
                            "exigidas": str(required_weeks),
                            "deficit": str(deficit),
                        },
                        effective_contributions_selected=[],
                        ibl_method_chosen="ERROR_IPC_FALTANTE",
                        ibl_final=None,
                        smlmv_ref=str(smlmv_ref),
                        s_factor=None,
                        replacement_rate_initial_pct=None,
                        additional_weeks_blocks=None,
                        replacement_rate_final_pct=None,
                        gross_pension=None,
                        limit_applied="BLOQUEADO_POR_IPC_FALTANTE",
                        health_discount_pct=None,
                        health_discount_amount=None,
                        fsp_discount_pct=None,
                        fsp_discount_amount=None,
                        net_pension_after_discounts=None,
                        real_purchasing_power_cop=None,
                        smlmv_multiples=None,
                        is_blocked=True,
                        blocking_reason="IPC_FALTANTE_HISTORICO",
                        step_by_step_operations=desglose,
                        data_version_used=f"Rev {historia.revision_version} ({historia.revision_id})",
                        provenance_counts={
                            "PDF": sum(
                                1
                                for r in historia.registros
                                if r.origen == ProvenanceType.PDF
                                and not r.excluido_del_calculo
                            ),
                            "DECLARACION_USUARIO": sum(
                                1
                                for r in historia.registros
                                if r.origen == ProvenanceType.DECLARACION_USUARIO
                                and not r.excluido_del_calculo
                            ),
                            "CORRECCION_MANUAL": sum(
                                1
                                for r in historia.registros
                                if r.origen == ProvenanceType.CORRECCION_MANUAL
                                and not r.excluido_del_calculo
                            ),
                            "EXCLUIDO": sum(
                                1 for r in historia.registros if r.excluido_del_calculo
                            ),
                        },
                    ),
                )
                AuditService.log_technical(
                    execution_id,
                    AuditStep.LIQUIDACION_PENSIONAL,
                    "PensionEngine",
                    0.0,
                    AuditSeverity.BLOQUEADO,
                    EventCode.IPC_FALTANTE,
                    "BLOQUEADO",
                    "Dato mensual del IPC no disponible",
                    "Verificar serie DANE o suministrar índices oficiales",
                )

            return SimulationResult(
                escenario_id=escenario.escenario_id,
                escenario_nombre=escenario.nombre,
                fecha_cumplimiento_edad_legal=horizon_date,
                edad_legal=legal_age,
                ya_supero_edad_legal=ya_supero_edad,
                semanas_exigidas=required_weeks,
                semanas_acreditadas_documentales=semanas_doc,
                semanas_recalculadas_calendario=semanas_cal,
                diferencia_semanas_recalculadas=diferencia_cal,
                semanas_futuras_proyectadas=semanas_proyectadas,
                semanas_totales_a_la_edad=semanas_totales,
                cumple_semanas=cumple_semanas,
                deficit_semanas=deficit,
                excedente_semanas=excedente,
                ibl_ultimos_10_anos=None,
                ibl_toda_la_vida=None,
                metodo_ibl_seleccionado="ERROR_IPC_FALTANTE",
                ibl_final=None,
                smlmv_referencia_retiro=smlmv_ref,
                s_factor=None,
                tasa_reemplazo_inicial_pct=None,
                semanas_adicionales_computables=None,
                bloques_completos_50_semanas=None,
                incremento_tasa_pct=None,
                tasa_reemplazo_final_pct=None,
                mesada_bruta=None,
                limite_aplicado="BLOQUEADO_POR_IPC_FALTANTE",
                descuento_salud_pct=None,
                descuento_salud_monto=None,
                descuento_fsp_pct=None,
                descuento_fsp_monto=None,
                valor_despues_descuentos=None,
                valor_real_poder_adquisitivo=None,
                equivalente_smlmv=None,
                mensaje_advertencia=advertencia,
                desglose_explicativo=desglose,
                requiere_revision_discrepancia=requiere_revision_discrepancia,
                bloqueado_por_ipc=True,
            )

        desglose.append(
            f"IBL últimos 10 años cotizados: ${ibl_10y:,.0f} COP."
            if ibl_10y
            else "IBL 10 años no liquidable."
        )
        if ibl_all:
            desglose.append(f"IBL promedio toda la vida laboral: ${ibl_all:,.0f} COP.")
        desglose.append(
            f"Método seleccionado: {metodo_ibl}. IBL aplicado: ${ibl_final:,.0f} COP."
        )

        # 4. Replacement rate
        s_factor, tasa_ini, sem_adic, bloques, inc_tasa, tasa_final = (
            self.calculate_replacement_rate(
                ibl=ibl_final,
                smlmv_ref=smlmv_ref,
                total_weeks=semanas_totales,
                required_weeks=required_weeks,
            )
        )

        desglose.append(
            f"Fórmula Ley 797 Art. 10: s = {s_factor:.4f} SMLMV. Tasa base: {tasa_ini:.2f}%. "
            f"Semanas adicionales: {sem_adic} ({bloques} bloques completos de 50 semanas -> +{inc_tasa:.2f}%). "
            f"Tasa de reemplazo final: {tasa_final:.2f}% (tope legal 80%)."
        )

        mesada_calculada = (ibl_final * (tasa_final / Decimal(100))).quantize(
            Decimal(1), rounding=ROUND_HALF_UP
        )

        # Min and Max legal limits
        limite_aplicado = "NINGUNO"
        mesada_bruta = mesada_calculada

        if mesada_bruta < smlmv_ref:
            mesada_bruta = smlmv_ref
            limite_aplicado = "MINIMA_1_SMLMV"
            desglose.append(
                f"Garantía de pensión mínima aplicada: se eleva a 1 SMLMV (${smlmv_ref:,.0f} COP)."
            )
        elif mesada_bruta > (smlmv_ref * Decimal(25)):
            mesada_bruta = smlmv_ref * Decimal(25)
            limite_aplicado = "MAXIMA_25_SMLMV"
            desglose.append(
                f"Tope máximo pensional aplicado: 25 SMLMV (${mesada_bruta:,.0f} COP)."
            )

        # Deductions
        salud_pct, salud_monto, fsp_pct, fsp_monto, valor_despues = (
            self.calculate_deductions(mesada_bruta, smlmv_ref)
        )

        desglose.append(
            f"Descuentos de ley: Salud ({salud_pct}% = ${salud_monto:,.0f} COP) + FSP Subsistencia ({fsp_pct}% = ${fsp_monto:,.0f} COP). "
            f"Valor estimado después de descuentos: ${valor_despues:,.0f} COP."
        )

        # Real valuation
        val = scenario_projector.convert_valuation(
            valor_despues, horizon_date.year, horizon_date.month
        )

        advertencia = "Estimación informativa basada en los datos y supuestos indicados. El reconocimiento corresponde a Colpensiones."

        if execution_id:
            AuditService.add_scenario_audit(
                execution_id,
                ScenarioCalculationAudit(
                    scenario_id=escenario.escenario_id,
                    scenario_name=escenario.nombre,
                    fixed_horizon_date=horizon_date.isoformat(),
                    legal_retirement_age=legal_age,
                    inputs=scenario_inputs,
                    generated_future_periods_count=len(projected_future_records),
                    weeks_breakdown={
                        "documentales": str(semanas_doc),
                        "declaradas_adicionales": str(semanas_declaradas),
                        "calendario": str(semanas_cal),
                        "proyectadas": str(semanas_proyectadas),
                        "totales": str(semanas_totales),
                        "exigidas": str(required_weeks),
                        "deficit": str(deficit),
                    },
                    effective_contributions_selected=effective_selected,
                    ibl_method_chosen=metodo_ibl,
                    ibl_final=str(ibl_final),
                    smlmv_ref=str(smlmv_ref),
                    s_factor=f"{s_factor:.4f}" if s_factor is not None else None,
                    replacement_rate_initial_pct=f"{tasa_ini:.2f}"
                    if tasa_ini is not None
                    else None,
                    additional_weeks_blocks=bloques,
                    replacement_rate_final_pct=f"{tasa_final:.2f}"
                    if tasa_final is not None
                    else None,
                    gross_pension=str(mesada_bruta),
                    limit_applied=limite_aplicado,
                    health_discount_pct=f"{salud_pct:.2f}",
                    health_discount_amount=str(salud_monto),
                    fsp_discount_pct=f"{fsp_pct:.2f}",
                    fsp_discount_amount=str(fsp_monto),
                    net_pension_after_discounts=str(valor_despues),
                    real_purchasing_power_cop=str(val.real_base_cop),
                    smlmv_multiples=f"{val.smlmv_multiples:.2f}",
                    is_blocked=False,
                    blocking_reason=None,
                    step_by_step_operations=desglose,
                    data_version_used=f"Rev {historia.revision_version} ({historia.revision_id})",
                    provenance_counts={
                        "PDF": sum(
                            1
                            for r in historia.registros
                            if r.origen == ProvenanceType.PDF
                            and not r.excluido_del_calculo
                        ),
                        "DECLARACION_USUARIO": sum(
                            1
                            for r in historia.registros
                            if r.origen == ProvenanceType.DECLARACION_USUARIO
                            and not r.excluido_del_calculo
                        ),
                        "CORRECCION_MANUAL": sum(
                            1
                            for r in historia.registros
                            if r.origen == ProvenanceType.CORRECCION_MANUAL
                            and not r.excluido_del_calculo
                        ),
                        "EXCLUIDO": sum(
                            1 for r in historia.registros if r.excluido_del_calculo
                        ),
                    },
                ),
            )
            AuditService.log_technical(
                execution_id,
                AuditStep.PROYECCION_ESCENARIO,
                "PensionEngine",
                0.0,
                AuditSeverity.INFO,
                EventCode.SIMULACION_COMPLETADA,
                "COMPLETADO",
                "Simulación de escenario completada exitosamente",
                "Ninguna",
            )

        return SimulationResult(
            escenario_id=escenario.escenario_id,
            escenario_nombre=escenario.nombre,
            fecha_cumplimiento_edad_legal=horizon_date,
            edad_legal=legal_age,
            ya_supero_edad_legal=ya_supero_edad,
            semanas_exigidas=required_weeks,
            semanas_acreditadas_documentales=semanas_doc,
            semanas_recalculadas_calendario=semanas_cal,
            diferencia_semanas_recalculadas=diferencia_cal,
            semanas_futuras_proyectadas=semanas_proyectadas,
            semanas_totales_a_la_edad=semanas_totales,
            cumple_semanas=True,
            deficit_semanas=Decimal(0),
            excedente_semanas=excedente,
            ibl_ultimos_10_anos=ibl_10y,
            ibl_toda_la_vida=ibl_all,
            metodo_ibl_seleccionado=metodo_ibl,
            ibl_final=ibl_final,
            smlmv_referencia_retiro=smlmv_ref,
            s_factor=s_factor,
            tasa_reemplazo_inicial_pct=tasa_ini,
            semanas_adicionales_computables=sem_adic,
            bloques_completos_50_semanas=bloques,
            incremento_tasa_pct=inc_tasa,
            tasa_reemplazo_final_pct=tasa_final,
            mesada_bruta=mesada_bruta,
            limite_aplicado=limite_aplicado,
            descuento_salud_pct=salud_pct,
            descuento_salud_monto=salud_monto,
            descuento_fsp_pct=fsp_pct,
            descuento_fsp_monto=fsp_monto,
            valor_despues_descuentos=valor_despues,
            valor_real_poder_adquisitivo=val.real_base_cop,
            equivalente_smlmv=val.smlmv_multiples,
            mensaje_advertencia=advertencia,
            desglose_explicativo=desglose,
            requiere_revision_discrepancia=requiere_revision_discrepancia,
        )
