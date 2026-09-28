"""Official Legal Rules Catalog for MiPensiónCO.

Baseline legal audit date: 2026-09-27.
Contains verified statutory articles, Constitutional Court rulings, Supreme Court of
Justice jurisprudence, and Colpensiones administrative instructions.
"""

from datetime import date

from src.legal.models import LegalRule, RuleStatus

CONSULTATION_DATE_BASELINE = date(2026, 9, 27)

RULES_REGISTRY: dict[str, LegalRule] = {
    "RULE-TRANS-2381-ART75": LegalRule(
        rule_id="RULE-TRANS-2381-ART75",
        norma="Ley 2381 de 2024",
        articulo_o_sentencia="Artículo 75 (Régimen de Transición)",
        url_oficial="https://normativa.colpensiones.gov.co/compilacion/docs/ley_2381_2024.htm",
        fecha_consulta=CONSULTATION_DATE_BASELINE,
        periodo_aplicacion="A partir de la entrada en vigor del sistema (1 de abril de 2027 según C-264/2026)",
        parametros={
            "umbral_mujeres_semanas": 750,
            "umbral_hombres_semanas": 900,
            "entidades_admitidas": [
                "Colpensiones",
                "Fondos Privados (RAIS)",
                "Tiempos Públicos Certificados",
            ],
        },
        interpretacion_implementada=(
            "Conserva la aplicación íntegra de la Ley 100 de 1993 y sus normas modificatorias para afiliados "
            "que acrediten al menos 750 semanas (mujeres) o 900 semanas (hombres) a la fecha de corte oficial. "
            "No se deben computar semanas posteriores a la fecha de corte para superar el umbral."
        ),
        pruebas_asociadas=[
            "test_transition_threshold_women_750_exact",
            "test_transition_threshold_men_900_exact",
            "test_transition_threshold_women_749_no_round",
            "test_transition_threshold_men_899_no_round",
            "test_transition_post_cutoff_weeks_excluded",
        ],
        estado=RuleStatus.VERIFICADA,
        notas_adicionales="No confundir con el traslado de régimen del artículo 76.",
    ),
    "RULE-CONST-C264-2026": LegalRule(
        rule_id="RULE-CONST-C264-2026",
        norma="Corte Constitucional, Sentencia C-264 de 2026",
        articulo_o_sentencia="Resolutivo Cuarto y Resolutivo Primero",
        url_oficial="https://www.corteconstitucional.gov.co/relatoria/2026/C-264-26.htm",
        fecha_consulta=CONSULTATION_DATE_BASELINE,
        periodo_aplicacion="Vigencia modulada: 1 de abril de 2027 para disposiciones exequibles",
        parametros={
            "fecha_entrada_vigor_diferida": "2027-04-01",
            "alcance": "Modulación de entrada en vigor y condicionamiento de disposiciones",
        },
        interpretacion_implementada=(
            "La sentencia C-264 de 2026 fija el 1 de abril de 2027 para la entrada en vigor de las disposiciones "
            "declaradas exequibles en su resolutivo primero; otras disposiciones quedan condicionadas a subsanación. "
            "No se describe la reforma como uniformemente vigente, derogada o suspendida. La evaluación distingue "
            "el régimen aplicable hoy, la evaluación de transición y las reglas de proyección futura."
        ),
        pruebas_asociadas=[
            "test_transition_future_cutoff_evaluation_status",
            "test_c264_differentiated_regime_application",
        ],
        estado=RuleStatus.VERIFICADA,
        notas_adicionales="Distingue vigencia actual de vigencia diferida.",
    ),
    "RULE-TRANS-TRASLADO-ART76": LegalRule(
        rule_id="RULE-TRANS-TRASLADO-ART76",
        norma="Ley 2381 de 2024",
        articulo_o_sentencia="Artículo 76 (Oportunidad de Traslado)",
        url_oficial="https://normativa.colpensiones.gov.co/compilacion/docs/ley_2381_2024.htm",
        fecha_consulta=CONSULTATION_DATE_BASELINE,
        periodo_aplicacion="Ventana de oportunidad de 2 años tras expedición de la ley",
        parametros={
            "aplica_traslado_entre_regimenes": True,
            "aplica_afiliados_ya_en_colpensiones": False,
        },
        interpretacion_implementada=(
            "La oportunidad de traslado y el requisito de doble asesoría aplican para traslados entre regímenes "
            "(ej. de fondo privado a Colpensiones). No se deben exigir automáticamente estas condiciones de edad "
            "y doble asesoría a quien ya pertenece a Colpensiones."
        ),
        pruebas_asociadas=["test_art76_not_demanded_for_colpensiones_native"],
        estado=RuleStatus.VERIFICADA,
    ),
    "RULE-RETIREMENT-AGE-L797": LegalRule(
        rule_id="RULE-RETIREMENT-AGE-L797",
        norma="Ley 797 de 2003",
        articulo_o_sentencia="Artículo 9 (Modificatorio del artículo 33 de la Ley 100 de 1993)",
        url_oficial="https://normativa.colpensiones.gov.co/compilacion/docs/ley_0797_2003.htm",
        fecha_consulta=CONSULTATION_DATE_BASELINE,
        periodo_aplicacion="1 de enero de 2014 en adelante",
        parametros={
            "edad_mujeres": 57,
            "edad_hombres": 62,
            "semanas_ordinarias_hombres": 1300,
            "semanas_ordinarias_mujeres_base": 1300,
        },
        interpretacion_implementada=(
            "La edad ordinaria de jubilación es de 57 años para mujeres y 62 años para hombres. "
            "Para hombres el requisito general de semanas es 1.300 semanas. Alcanzar la edad legal "
            "determina el horizonte de simulación, no una obligación de retiro ni una garantía de cobro inmediato."
        ),
        pruebas_asociadas=[
            "test_legal_age_horizon_male",
            "test_legal_age_horizon_female",
            "test_no_payable_mesada_if_deficit",
        ],
        estado=RuleStatus.VERIFICADA,
    ),
    "RULE-WOMEN-REDUCTION-C197": LegalRule(
        rule_id="RULE-WOMEN-REDUCTION-C197",
        norma="Corte Constitucional, Sentencia C-197 de 2023",
        articulo_o_sentencia="Resolutivo de inexequibilidad diferida y tabla de progresividad",
        url_oficial="https://normativa.colpensiones.gov.co/compilacion/docs/C-197_2023.htm",
        fecha_consulta=CONSULTATION_DATE_BASELINE,
        periodo_aplicacion="1 de enero de 2026 en adelante",
        parametros={
            "tabla_reduccion_mujeres": {
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
            }
        },
        interpretacion_implementada=(
            "Para mujeres, el requisito de semanas se reduce progresivamente a partir de 2026 (1.250 semanas) "
            "disminuyendo 25 semanas cada año hasta alcanzar 1.000 semanas en 2036. El requisito exigible "
            "se determina según el año exacto en que la mujer cumple la edad legal de retiro (57 años). "
            "No se incorpora automáticamente la reducción por hijos sin verificación específica."
        ),
        pruebas_asociadas=[
            "test_women_weeks_schedule_by_year_2025_to_2036",
            "test_women_requirement_selected_by_horizon_date",
        ],
        estado=RuleStatus.VERIFICADA,
        notas_adicionales="Confirmado operativamente por Colpensiones en comunicado oficial de 2026.",
    ),
    "RULE-WEEK-CALENDAR-SL138": LegalRule(
        rule_id="RULE-WEEK-CALENDAR-SL138",
        norma="Corte Suprema de Justicia, Sala Laboral",
        articulo_o_sentencia="Sentencia SL138-2024",
        url_oficial="https://cortesuprema.gov.co/semanas-de-cotizacion-a-pension-se-deben-contabilizar-con-dias-calendario-no-con-meses-de-30-dias/",
        fecha_consulta=CONSULTATION_DATE_BASELINE,
        periodo_aplicacion="Jurisprudencia vinculante para contabilización pensional",
        parametros={
            "dias_por_semana": 7,
            "metodo_computo": "dias_calendario_reales",
            "mes_comercial_facturacion": 30,
        },
        interpretacion_implementada=(
            "Distingue el mes comercial de 30 días utilizado para facturación y cobro de aportes, del cómputo "
            "por días calendario reales para establecer semanas de pensión (cada 7 días de cotización efectiva "
            "equivalen a una semana). No duplicar días por cotizaciones simultáneas y contemplar años bisiestos. "
            "Se conserva el total reconocido por Colpensiones y se contrasta con el recálculo calendario sin sustitución silenciosa."
        ),
        pruebas_asociadas=[
            "test_week_computation_seven_days_calendar",
            "test_leap_year_february_29_included",
            "test_simultaneous_employers_no_duplication",
            "test_recognized_vs_calendar_difference_reported",
        ],
        estado=RuleStatus.VERIFICADA,
    ),
    "RULE-IBL-ORDINARY-L100-ART21": LegalRule(
        rule_id="RULE-IBL-ORDINARY-L100-ART21",
        norma="Ley 100 de 1993",
        articulo_o_sentencia="Artículo 21 (Ingreso Base de Liquidación)",
        url_oficial="https://normograma.sena.edu.co/compilacion/docs/ley_0100_1993.htm",
        fecha_consulta=CONSULTATION_DATE_BASELINE,
        periodo_aplicacion="Vigente desde 1994",
        parametros={
            "opcion_ordinaria_anos": 10,
            "umbral_semanas_toda_la_vida": 1250,
            "actualizacion_ipc": True,
        },
        interpretacion_implementada=(
            "El IBL ordinario se calcula actualizando los salarios devengados con el IPC anual. Procede la opción "
            "de promedio de toda la vida laboral únicamente cuando el afiliado acredite al menos 1.250 semanas cotizadas "
            "y este promedio resulte superior al de los últimos 10 años. La reducción de semanas para mujeres no rebaja "
            "el requisito específico de 1.250 semanas para la opción de toda la vida."
        ),
        pruebas_asociadas=[
            "test_ibl_lifetime_selection_only_with_1250_weeks",
            "test_ibl_lifetime_selected_when_higher",
            "test_women_reduction_does_not_lower_1250_lifetime_threshold",
        ],
        estado=RuleStatus.VERIFICADA,
    ),
    "RULE-IBL-EFFECTIVE-SL18546": LegalRule(
        rule_id="RULE-IBL-EFFECTIVE-SL18546",
        norma="Corte Suprema de Justicia, Sala Laboral",
        articulo_o_sentencia="Sentencia SL18546-2016",
        url_oficial="https://www.cortesuprema.gov.co/corte/wp-content/uploads/relatorias/la/babr2017/SL18546-2016.pdf",
        fecha_consulta=CONSULTATION_DATE_BASELINE,
        periodo_aplicacion="Jurisprudencia vinculante",
        parametros={
            "criterio_10_anos": "cotizaciones_efectivas",
            "inclusion_lagunas_como_cero": False,
        },
        interpretacion_implementada=(
            "Los últimos diez años para el cálculo del IBL corresponden a los últimos diez años de cotizaciones efectivas "
            "(equivalentes a 3.650 días cotizados o el tiempo acreditado retroactivamente). No se deben tomar mecánicamente "
            "los últimos 120 meses calendario rellenando lagunas laborales como ingresos cero."
        ),
        pruebas_asociadas=[
            "test_ibl_effective_ten_years_skips_calendar_gaps",
            "test_ibl_weighted_by_cotized_days_not_simple_mean",
        ],
        estado=RuleStatus.VERIFICADA,
    ),
    "RULE-REPLACEMENT-RATE-L797": LegalRule(
        rule_id="RULE-REPLACEMENT-RATE-L797",
        norma="Ley 797 de 2003",
        articulo_o_sentencia="Artículo 10 (Modificatorio del artículo 34 de la Ley 100 de 1993)",
        url_oficial="https://normativa.colpensiones.gov.co/compilacion/docs/ley_0797_2003.htm",
        fecha_consulta=CONSULTATION_DATE_BASELINE,
        periodo_aplicacion="2004 en adelante",
        parametros={
            "tasa_base": 65.50,
            "factor_sensibilidad": 0.50,
            "incremento_por_bloque": 1.50,
            "tamano_bloque_semanas": 50,
            "tope_porcentual_maximo": 80.00,
        },
        interpretacion_implementada=(
            "Para el régimen ordinario: s = IBL / SMLMV de referencia. Tasa inicial (%) = 65.50 - 0.50 * s. "
            "Por cada bloque completo de 50 semanas adicionales a las mínimas requeridas se incrementa 1.5 puntos "
            "porcentuales, hasta el tope del 80%."
        ),
        pruebas_asociadas=[
            "test_replacement_rate_initial_formula",
            "test_replacement_rate_49_weeks_no_increment",
            "test_replacement_rate_50_weeks_adds_one_point_five",
            "test_replacement_rate_capped_at_80_percent",
        ],
        estado=RuleStatus.VERIFICADA,
    ),
    "RULE-NO-UNIVERSAL-1800-SL810": LegalRule(
        rule_id="RULE-NO-UNIVERSAL-1800-SL810",
        norma="Corte Suprema de Justicia, Sala Laboral",
        articulo_o_sentencia="Sentencias SL3501-2022 y SL810-2023",
        url_oficial="https://www.cortesuprema.gov.co/corte/wp-content/uploads/relatorias/la/bjun2023/SL810-2023.pdf",
        fecha_consulta=CONSULTATION_DATE_BASELINE,
        periodo_aplicacion="Jurisprudencia vinculante",
        parametros={
            "limite_estricto_1800_semanas": False,
            "permite_computar_mas_de_1800_hasta_80_porciento": True,
        },
        interpretacion_implementada=(
            "No existe un límite universal e infranqueable de 1.800 semanas que impida seguir incrementando la tasa "
            "cuando el afiliado aún no ha alcanzado el tope máximo legal del 80%. Las semanas adicionales a 1.800 "
            "se computan en bloques de 50 si se requiere para llegar al 80%."
        ),
        pruebas_asociadas=["test_weeks_over_1800_can_increase_rate_up_to_80_cap"],
        estado=RuleStatus.VERIFICADA,
    ),
    "RULE-MIN-MAX-PENSION-L100": LegalRule(
        rule_id="RULE-MIN-MAX-PENSION-L100",
        norma="Ley 100 de 1993",
        articulo_o_sentencia="Artículos 18, 34 y 35 (Monto Mínimo y Máximo de Pensión)",
        url_oficial="https://normativa.colpensiones.gov.co/compilacion/docs/ley_0100_1993.htm",
        fecha_consulta=CONSULTATION_DATE_BASELINE,
        periodo_aplicacion="Vigente",
        parametros={
            "monto_minimo_smlmv": 1.0,
            "monto_maximo_smlmv": 25.0,
        },
        interpretacion_implementada=(
            "Ninguna pensión de vejez en Colpensiones puede ser inferior a un (1) SMLMV vigente a la fecha de causación, "
            "ni superior a veinticinco (25) SMLMV. La garantía de pensión mínima puede producir una relación efectiva "
            "pensión/IBL superior al tope aritmético del 80% de la fórmula; no se debe truncar erróneamente por debajo de 1 SMLMV."
        ),
        pruebas_asociadas=[
            "test_minimum_pension_guarantee_one_smlmv",
            "test_maximum_pension_cap_twenty_five_smlmv",
        ],
        estado=RuleStatus.VERIFICADA,
    ),
    "RULE-HEALTH-DISCOUNT-L2010": LegalRule(
        rule_id="RULE-HEALTH-DISCOUNT-L2010",
        norma="Ley 2010 de 2019, Ley 2294 de 2023 y Circulares Colpensiones",
        articulo_o_sentencia="Aportes a salud de pensionados vigentes desde 2024",
        url_oficial="https://www.colpensiones.gov.co/publicaciones/4994/el-presidente-de-colpensiones-aplicara-reduccion-de-aporte-en-salud-a-pensiones-entre-2-y-3-salarios-minimos/",
        fecha_consulta=CONSULTATION_DATE_BASELINE,
        periodo_aplicacion="Vigente desde 2024",
        parametros={
            "rangos_salud": [
                {"min_smlmv": 0.0, "max_smlmv": 1.0, "porcentaje": 4.0},
                {"min_smlmv": 1.0, "max_smlmv": 3.0, "porcentaje": 10.0},
                {"min_smlmv": 3.0, "max_smlmv": 999.0, "porcentaje": 12.0},
            ]
        },
        interpretacion_implementada=(
            "El aporte a salud obligatorio a cargo del pensionado ordinario residente en Colombia es: "
            "Exactamente 1 SMLMV: 4%; superior a 1 y hasta 3 SMLMV: 10%; superior a 3 SMLMV: 12%. "
            "No se aplica automáticamente si el afiliado reside en el exterior o tiene régimen especial exceptuado."
        ),
        pruebas_asociadas=[
            "test_health_discount_one_smlmv_is_4_percent",
            "test_health_discount_between_1_and_3_smlmv_is_10_percent",
            "test_health_discount_above_3_smlmv_is_12_percent",
        ],
        estado=RuleStatus.VERIFICADA,
    ),
    "RULE-SOLIDARITY-FUND-D1833": LegalRule(
        rule_id="RULE-SOLIDARITY-FUND-D1833",
        norma="Decreto 1833 de 2016",
        articulo_o_sentencia="Artículo 2.2.14.1.38 (Aporte a Subcuenta de Subsistencia por Pensionados)",
        url_oficial="https://normativa.colpensiones.gov.co/colpens/docs/decreto_1833_2016_pr021.htm",
        fecha_consulta=CONSULTATION_DATE_BASELINE,
        periodo_aplicacion="Vigente",
        parametros={
            "rango_10_a_20_smlmv": 1.0,
            "rango_mas_de_20_smlmv": 2.0,
        },
        interpretacion_implementada=(
            "Los pensionados cuya mesada supere los 10 SMLMV y hasta 20 SMLMV aportan un 1.0% adicional con destino a la "
            "subcuenta de subsistencia del Fondo de Solidaridad Pensional. Para mesadas superiores a 20 SMLMV, el aporte es del 2.0%."
        ),
        pruebas_asociadas=[
            "test_solidarity_fund_between_10_and_20_smlmv",
            "test_solidarity_fund_above_20_smlmv",
        ],
        estado=RuleStatus.VERIFICADA,
    ),
    "RULE-SPECIAL-REGIMES-SCOPE": LegalRule(
        rule_id="RULE-SPECIAL-REGIMES-SCOPE",
        norma="Ley 100 de 1993 y Estatutos Especiales",
        articulo_o_sentencia="Artículos 36, 140, 279 y Decretos de Alto Riesgo (Dec. 2090/2003)",
        url_oficial="https://normativa.colpensiones.gov.co/compilacion/docs/ley_0100_1993.htm",
        fecha_consulta=CONSULTATION_DATE_BASELINE,
        periodo_aplicacion="Vigente",
        parametros={
            "regimenes_especiales_soportados_en_simulador_ordinario": False,
        },
        interpretacion_implementada=(
            "Casos con régimen de transición antiguo (Art. 36 Ley 100), actividades de alto riesgo (Decreto 2090/2003), "
            "pensión familiar, invalidez, sobrevivientes, tiempos internacionales sin totalizar, o pensionados que solicitan "
            "reliquidación, son clasificados como 'CASO_JURIDICO_ESPECIAL' o 'AFILIACION_FUERA_DE_ALCANCE'. El simulador no "
            "les aplica mecánicamente la fórmula ordinaria y explica la razón jurídica."
        ),
        pruebas_asociadas=["test_special_regimes_classified_out_of_scope"],
        estado=RuleStatus.VERIFICADA,
    ),
}


class LegalCatalog:
    """Independent query catalog for statutory and jurisprudential rules."""

    @classmethod
    def get_rule(cls, rule_id: str) -> LegalRule | None:
        return RULES_REGISTRY.get(rule_id)

    @classmethod
    def list_all_rules(cls) -> list[LegalRule]:
        return list(RULES_REGISTRY.values())

    @classmethod
    def list_rules_by_status(cls, status: RuleStatus) -> list[LegalRule]:
        return [r for r in RULES_REGISTRY.values() if r.estado == status]
