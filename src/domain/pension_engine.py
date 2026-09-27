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

from datetime import date, timedelta
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

from src.domain.models import (
    AffiliationStatus,
    CotizacionRecord,
    EscenarioConfig,
    HistoriaLaboral,
    SexCategory,
    SimulationResult,
    TransitionEvaluation,
    TransitionStatus,
)
from src.economic.ipc import calculate_ipc_adjustment_factor
from src.economic.projector import EconomicProjector

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
    ) -> TransitionEvaluation:
        """Evaluates whether affiliate preserves Ley 100 transition under Ley 2381 Art. 75 and C-264/2026."""
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
        accredited_days_to_cutoff: set[date] = set()
        for r in historia.registros:
            if r.periodo_inicio <= cutoff_date:
                # Clip period to cutoff
                p_end = min(r.periodo_fin, cutoff_date)
                cur = r.periodo_inicio
                while cur <= p_end:
                    accredited_days_to_cutoff.add(cur)
                    cur += timedelta(days=1)

        # Convert unique calendar days to weeks (7 days = 1 week per SL138-2024)
        semanas_al_corte = (
            Decimal(len(accredited_days_to_cutoff)) / Decimal(7)
        ).quantize(Decimal("0.01"), rounding=ROUND_FLOOR)

        # If the report was updated on or before the cutoff date (or if all contributions are before cutoff),
        # the documentary summary recognized by Colpensiones is valid documentary evidence
        latest_record_date = (
            max([r.periodo_fin for r in historia.registros])
            if historia.registros
            else None
        )
        report_date = historia.fecha_actualizacion_reporte or latest_record_date

        if historia.semanas_resumen_colpensiones > Decimal(0):
            if report_date and report_date <= cutoff_date:
                semanas_al_corte = max(
                    semanas_al_corte, historia.semanas_resumen_colpensiones
                )
            elif not historia.registros:
                semanas_al_corte = historia.semanas_resumen_colpensiones

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
    def compute_calendar_weeks(cls, registros: list[CotizacionRecord]) -> Decimal:
        """Computes total weeks using exact calendar days (SL138-2024: 7 days = 1 week).

        Eliminates duplicate days caused by simultaneous employers.
        """
        cotized_days: set[date] = set()
        for r in registros:
            cur = r.periodo_inicio
            while cur <= r.periodo_fin:
                cotized_days.add(cur)
                cur += timedelta(days=1)
        return (Decimal(len(cotized_days)) / Decimal(7)).quantize(
            Decimal("0.01"), rounding=ROUND_FLOOR
        )

    def calculate_ibl(
        self,
        historia: HistoriaLaboral,
        target_year: int,
        target_month: int,
        assumed_inflation: Decimal = Decimal("0.04"),
    ) -> tuple[Decimal | None, Decimal | None, str, Decimal]:
        """Calculates IBL comparing 10-year effective cotizaciones vs lifetime average.

        Under SL18546-2016, 10 years means 3,650 days of effective cotizaciones (not calendar months).
        Under Ley 100 Art. 21, lifetime average is only accessible if total accredited weeks >= 1,250.
        """
        sorted_records = sorted(
            historia.registros, key=lambda r: r.periodo_fin, reverse=True
        )
        if not sorted_records:
            return None, None, "SIN_REGISTROS", Decimal(0)

        # 1. 10 years of effective contributions (3,650 days)
        effective_days_needed = 3650
        accumulated_days_10y = 0
        weighted_ibc_sum_10y = Decimal(0)

        for r in sorted_records:
            dias_en_registro = max(1, r.dias_cotizados)
            dias_a_tomar = min(
                dias_en_registro, effective_days_needed - accumulated_days_10y
            )

            factor_ipc = calculate_ipc_adjustment_factor(
                initial_year=r.periodo_fin.year,
                initial_month=r.periodo_fin.month,
                target_year=target_year,
                target_month=target_month,
                assumed_annual_inflation=assumed_inflation,
            )
            ibc_actualizado = r.ibc * factor_ipc
            weighted_ibc_sum_10y += ibc_actualizado * Decimal(dias_a_tomar)
            accumulated_days_10y += dias_a_tomar

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
        total_weeks = self.compute_calendar_weeks(historia.registros)
        total_days_all = sum(r.dias_cotizados for r in historia.registros)
        weighted_ibc_sum_all = Decimal(0)

        for r in historia.registros:
            factor_ipc = calculate_ipc_adjustment_factor(
                initial_year=r.periodo_fin.year,
                initial_month=r.periodo_fin.month,
                target_year=target_year,
                target_month=target_month,
                assumed_annual_inflation=assumed_inflation,
            )
            weighted_ibc_sum_all += (r.ibc * factor_ipc) * Decimal(r.dias_cotizados)

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
            return ibl_10y, ibl_all, "TODA_LA_VIDA_SUPERIOR", ibl_all

        if ibl_10y is not None:
            return ibl_10y, ibl_all, "ULTIMOS_10_ANOS_EFECTIVOS", ibl_10y

        final_fallback = ibl_all or Decimal(0)
        return ibl_10y, ibl_all, "TOTAL_DISPONIBLE", final_fallback

    def calculate_replacement_rate(
        self,
        ibl: Decimal,
        smlmv_ref: Decimal,
        total_weeks: Decimal,
        required_weeks: int,
    ) -> tuple[Decimal, Decimal, int, Decimal, Decimal]:
        """Calculates replacement rate under Ley 797 Art. 10 & SL810-2023.

        Returns:
            (s_factor, tasa_inicial_pct, bloques_completos, incremento_pct, tasa_final_pct)
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
        )  # type: ignore

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

    def simulate_scenario(
        self,
        historia: HistoriaLaboral,
        escenario: EscenarioConfig,
        as_of_date: date | None = None,
    ) -> SimulationResult:
        """Executes complete deterministic simulation terminating strictly at legal retirement age."""
        today = as_of_date or date(2026, 9, 27)

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

        # 1. Accredited documentary and calendar weeks
        semanas_doc = historia.semanas_resumen_colpensiones
        semanas_cal = self.compute_calendar_weeks(historia.registros)
        diferencia_cal = (semanas_cal - semanas_doc).quantize(Decimal("0.01"))

        # Base weeks to use for baseline projection (we use documentary or calendar)
        base_weeks = max(semanas_doc, semanas_cal)

        # 2. Projected future weeks up to retirement horizon
        semanas_proyectadas = Decimal(0)
        if not ya_supero_edad:
            # Last recorded contribution date
            last_cot_date = (
                max([r.periodo_fin for r in historia.registros])
                if historia.registros
                else today
            )
            start_proj = max(last_cot_date + timedelta(days=1), today)

            if start_proj < horizon_date:
                # Iterate each day to check pause periods
                proj_days = 0
                cur = start_proj
                while cur < horizon_date:
                    # Check if day falls inside any non-contribution pause
                    in_pause = any(
                        p_start <= cur <= p_end
                        for p_start, p_end in escenario.periodos_sin_aporte
                    )
                    if not in_pause:
                        proj_days += 1
                    cur += timedelta(days=1)
                semanas_proyectadas = (Decimal(proj_days) / Decimal(7)).quantize(
                    Decimal("0.01"), rounding=ROUND_FLOOR
                )

        semanas_totales = (base_weeks + semanas_proyectadas).quantize(Decimal("0.01"))
        cumple_semanas = semanas_totales >= Decimal(required_weeks)

        deficit = max(Decimal(0), Decimal(required_weeks) - semanas_totales).quantize(
            Decimal("0.01")
        )
        excedente = max(Decimal(0), semanas_totales - Decimal(required_weeks)).quantize(
            Decimal("0.01")
        )

        smlmv_ref = self.projector.get_projected_smlmv(horizon_date.year)

        # Explanatory log
        desglose: list[str] = [
            f"Horizonte ordinario: {horizon_date.isoformat()} (cumplimiento de {legal_age} años).",
            f"Requisito legal aplicable ({horizon_date.year}): {required_weeks} semanas.",
            f"Semanas reconocidas documentales: {semanas_doc}. Semanas recalculadas por días calendario: {semanas_cal}.",
        ]

        if ya_supero_edad:
            desglose.append(
                "La persona ya superó la edad legal ordinaria. No se proyectan aportes futuros hacia una fecha pasada."
            )
        else:
            desglose.append(
                f"Semanas proyectadas hasta la edad legal: {semanas_proyectadas}."
            )

        desglose.append(f"Total semanas a la edad legal: {semanas_totales}.")

        # If deficit: NO PAYABLE MESADA ALLOWED
        if not cumple_semanas:
            desglose.append(
                f"DÉFICIT PENSIONAL: Faltan {deficit} semanas para reunir el requisito legal a la edad ordinaria."
            )
            desglose.append(
                "REGLA ESTRICTA DE PRODUCTO: No se calcula una mesada pagadera ni se proyectan aportes posteriores a la edad legal."
            )

            advertencia = "No cumple con las semanas mínimas requeridas a la edad legal ordinaria. No se reconoce mesada pensional."
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
                cumple_semanas=False,
                deficit_semanas=deficit,
                excedente_semanas=Decimal(0),
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
                limite_aplicado=None,
                descuento_salud_pct=None,
                descuento_salud_monto=None,
                descuento_fsp_pct=None,
                descuento_fsp_monto=None,
                valor_despues_descuentos=None,
                valor_real_poder_adquisitivo=None,
                equivalente_smlmv=None,
                mensaje_advertencia=advertencia,
                desglose_explicativo=desglose,
            )

        # If eligible, calculate IBL
        ibl_10y, ibl_all, metodo_ibl, ibl_final = self.calculate_ibl(
            historia=historia,
            target_year=horizon_date.year,
            target_month=horizon_date.month,
            assumed_inflation=escenario.supuesto_inflacion,
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

        # Replacement rate
        s_factor, tasa_ini, sem_adic, bloques, inc_tasa, tasa_final = (
            self.calculate_replacement_rate(  # type: ignore
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
        val = self.projector.convert_valuation(
            valor_despues, horizon_date.year, horizon_date.month
        )

        advertencia = "Estimación informativa basada en los datos y supuestos indicados. El reconocimiento corresponde a Colpensiones."

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
        )
