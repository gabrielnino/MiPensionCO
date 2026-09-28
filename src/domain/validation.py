"""Pure domain validation and reconciliation engine for labor history records.

Enforces Colombian legal pension rules and data integrity:
- Prevents inverted dates, negative values, and incompatible days.
- Detects duplicates and employer interval superpositions.
- Reconciles recognized summary weeks against detail and user declarations
  without arbitrarily choosing the highest total.
- Conforms strictly to Clean Code, SOLID, and static type safety.
"""

from dataclasses import replace
from decimal import Decimal
from typing import Any

from src.domain.models import (
    CotizacionRecord,
    HistoriaLaboral,
    ProvenanceType,
)
from src.domain.pension_engine import PensionEngine


def validate_cotizacion_record(record: CotizacionRecord) -> list[dict[str, str]]:
    """Validates an individual contribution record for consistency and plausibility.

    Returns:
        List of validation issues with code, message, and severity.
    """
    issues: list[dict[str, str]] = []

    # 1. Inverted dates
    if record.periodo_inicio > record.periodo_fin:
        issues.append(
            {
                "code": "FECHAS_INVERTIDAS",
                "message": (
                    f"La fecha de inicio ({record.periodo_inicio}) no puede ser "
                    f"posterior a la fecha de fin ({record.periodo_fin})."
                ),
                "severity": "ERROR",
            }
        )

    # 2. Negative values
    if record.dias_cotizados < 0 or record.dias_reportados < 0:
        issues.append(
            {
                "code": "VALOR_NEGATIVO_DIAS",
                "message": "Los días cotizados o reportados no pueden ser negativos.",
                "severity": "ERROR",
            }
        )

    if record.ibc < Decimal(0):
        issues.append(
            {
                "code": "VALOR_NEGATIVO_IBC",
                "message": "El Ingreso Base de Cotización (IBC) no puede ser negativo.",
                "severity": "ERROR",
            }
        )

    # 3. Incompatible days with calendar span
    if record.periodo_inicio <= record.periodo_fin:
        span_days = (record.periodo_fin - record.periodo_inicio).days + 1
        # Colombian statutory convention (Dec. 1406/1999 Art. 19 / PILA):
        # A full month of February (day 1 to 28/29) cotizado as 30 days is standard labor convention.
        is_full_february_convention = (
            record.periodo_inicio.month == 2
            and record.periodo_inicio.day == 1
            and span_days in (28, 29)
            and record.dias_cotizados <= 30
        )
        if record.dias_cotizados > span_days and not is_full_february_convention:
            issues.append(
                {
                    "code": "DIAS_INCOMPATIBLES_CON_PERIODO",
                    "message": (
                        f"Los días cotizados ({record.dias_cotizados}) exceden los "
                        f"días calendario del intervalo ({span_days} días)."
                    ),
                    "severity": "ERROR",
                }
            )

    # 4. Pending or missing data
    if record.dias_pendientes_validacion or (
        record.observaciones
        and any(
            flag in record.observaciones.upper()
            for flag in ("SIN_IBC", "DATO_AUSENTE", "PENDIENTE")
        )
    ):
        issues.append(
            {
                "code": "REQUIERE_REVISION_DATOS",
                "message": (
                    "El registro presenta datos incompletos o días pendientes de validación."
                ),
                "severity": "WARNING",
            }
        )

    # 5. Informational zero IBC (allowed for non-remunerated leaves)
    if record.ibc == Decimal(0) and not record.dias_pendientes_validacion:
        issues.append(
            {
                "code": "IBC_CERO_INFORMADO",
                "message": (
                    "IBC reportado en $0 COP (posible suspensión o licencia no remunerada)."
                ),
                "severity": "INFO",
            }
        )

    return issues


def validate_labor_history_periods(
    records: list[CotizacionRecord],
) -> list[dict[str, str]]:
    """Validates collective coherence across contribution records (duplicates, overlaps).

    Returns:
        List of issue dicts identifying duplicate or overlapping records.
    """
    issues: list[dict[str, str]] = []
    active = [r for r in records if not r.excluido_del_calculo]

    # Check for duplicates and overlaps
    seen_exact: set[tuple[str, str, str]] = set()

    for idx, r in enumerate(active):
        # Validate individual record first
        indiv_issues = validate_cotizacion_record(r)
        issues.extend(indiv_issues)

        # Exact duplicate check (same start, end, employer)
        key = (
            r.periodo_inicio.isoformat(),
            r.periodo_fin.isoformat(),
            r.aportante.strip().upper(),
        )
        if key in seen_exact:
            issues.append(
                {
                    "code": "REGISTRO_DUPLICADO",
                    "message": (
                        f"Registro duplicado para el aportante '{r.aportante}' "
                        f"en el período {r.periodo_inicio} a {r.periodo_fin}."
                    ),
                    "severity": "WARNING",
                }
            )
        else:
            seen_exact.add(key)

        # Overlap check with other records of the same employer
        for other in active[idx + 1 :]:
            if (
                r.aportante.strip().upper() == other.aportante.strip().upper()
                and r.periodo_inicio < other.periodo_fin
                and r.periodo_fin > other.periodo_inicio
            ):
                issues.append(
                    {
                        "code": "SUPERPOSICION_MISMO_APORTANTE",
                        "message": (
                            f"Períodos superpuestos del mismo aportante '{r.aportante}': "
                            f"[{r.periodo_inicio} - {r.periodo_fin}] con "
                            f"[{other.periodo_inicio} - {other.periodo_fin}]."
                        ),
                        "severity": "WARNING",
                    }
                )

    return issues


def reconcile_labor_history(historia: HistoriaLaboral) -> dict[str, Any]:
    """Reconciles recognized summary weeks from Colpensiones against recalculations

    from detail records and user declarations.
    Follows statutory fidelity: does NOT arbitrarily pick max(semanas_doc, semanas_cal).

    Returns:
        Dictionary of reconciliation metrics, differences, and pending items.
    """
    semanas_reconocidas_pdf = historia.semanas_resumen_colpensiones

    active_records = [r for r in historia.registros if not r.excluido_del_calculo]
    excluded_records = [r for r in historia.registros if r.excluido_del_calculo]

    pdf_detail = [r for r in active_records if r.origen == ProvenanceType.PDF]
    declared = [
        r for r in active_records if r.origen == ProvenanceType.DECLARACION_USUARIO
    ]
    corrected = [
        r for r in active_records if r.origen == ProvenanceType.CORRECCION_MANUAL
    ]

    # Use the same calendar convention and overlap policy as the simulation.
    reviewed_detail = pdf_detail + corrected
    semanas_recalculadas_detalle = PensionEngine.compute_calendar_weeks(reviewed_detail)
    semanas_declaradas, declared_overlap = PensionEngine.additional_declared_weeks(
        reviewed_detail, declared
    )
    semanas_excluidas = PensionEngine.compute_calendar_weeks(
        [replace(r, excluido_del_calculo=False) for r in excluded_records]
    )
    semanas_totales_activas = PensionEngine.compute_calendar_weeks(active_records)

    # Net difference between recognized PDF summary and recalculation
    diferencia = (semanas_recalculadas_detalle - semanas_reconocidas_pdf).quantize(
        Decimal("0.01")
    )
    boundaries = [750, 900]
    if historia.sexo is not None and historia.fecha_nacimiento is not None:
        horizon = PensionEngine.calculate_retirement_horizon_date(
            historia.fecha_nacimiento, historia.sexo
        )
        required = PensionEngine.get_required_weeks_for_year(
            horizon.year, historia.sexo
        )
        boundaries.extend(
            range(
                required,
                max(
                    required,
                    int(max(semanas_reconocidas_pdf, semanas_recalculadas_detalle)),
                )
                + 1,
                50,
            )
        )
    crosses_boundary = any(
        min(semanas_reconocidas_pdf, semanas_recalculadas_detalle)
        < boundary
        <= max(semanas_reconocidas_pdf, semanas_recalculadas_detalle)
        for boundary in boundaries
    )
    tiene_discrepancia = semanas_reconocidas_pdf > 0 and (
        abs(diferencia) >= Decimal("1.00") or crosses_boundary
    )

    # Pending matters checklist
    asuntos_pendientes: list[str] = []
    if tiene_discrepancia:
        asuntos_pendientes.append(
            f"Discrepancia de {abs(diferencia)} semanas entre el certificado de Colpensiones "
            f"({semanas_reconocidas_pdf} sem) y el recálculo del detalle ({semanas_recalculadas_detalle} sem)."
        )

    if historia.periodos_desconocidos_o_faltantes:
        asuntos_pendientes.append(
            "Existen períodos no informados o con vacíos de cotización en el reporte original."
        )

    if any(r.dias_pendientes_validacion for r in active_records):
        count_pend = sum(1 for r in active_records if r.dias_pendientes_validacion)
        asuntos_pendientes.append(
            f"Hay {count_pend} registro(s) con días pendientes de validación o sin días explícitos."
        )

    if excluded_records:
        asuntos_pendientes.append(
            f"Se han excluido voluntariamente {len(excluded_records)} registro(s) "
            f"({semanas_excluidas} semanas) del cálculo pensional."
        )

    if declared:
        asuntos_pendientes.append(
            f"Se han incorporado {len(declared)} período(s) declarado(s) por el usuario "
            f"({semanas_declaradas} semanas) como declaraciones bajo su responsabilidad."
        )

    validation_issues = validate_labor_history_periods(historia.registros)
    blocking_errors = [i for i in validation_issues if i["severity"] == "ERROR"]

    if not reviewed_detail:
        blocking_errors.append(
            {
                "message": "No hay detalle documental activo para conciliar las semanas. Revise la extracción del PDF."
            }
        )
    if tiene_discrepancia:
        blocking_errors.append({"message": asuntos_pendientes[0]})
    if declared_overlap:
        blocking_errors.append(
            {
                "message": "Superposición de declaraciones: requiere revisión antes de continuar."
            }
        )

    return {
        "semanas_reconocidas_pdf": semanas_reconocidas_pdf,
        "semanas_recalculadas_detalle": semanas_recalculadas_detalle,
        "semanas_declaradas_adicionales": semanas_declaradas,
        "semanas_excluidas": semanas_excluidas,
        "semanas_totales_activas": semanas_totales_activas,
        "diferencia_detalle_vs_reconocidas": diferencia,
        "tiene_discrepancia": tiene_discrepancia,
        "conteo_registros": {
            "total": len(historia.registros),
            "activos": len(active_records),
            "pdf": len(pdf_detail),
            "declarados": len(declared),
            "corregidos": len(corrected),
            "excluidos": len(excluded_records),
        },
        "asuntos_pendientes": asuntos_pendientes,
        "errores_bloqueantes": [e["message"] for e in blocking_errors],
        "permite_continuar": len(blocking_errors) == 0,
    }
