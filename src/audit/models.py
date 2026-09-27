"""Audit Models & Schemas for MiPensiónCO.

Strictly separates:
A. Technical event logs without PII (logs/technical_audit.log).
B. Full calculation and documentary audit with explicit local consent.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AuditSeverity(str, Enum):
    INFO = "INFO"
    ADVERTENCIA = "ADVERTENCIA"
    BLOQUEADO = "BLOQUEADO"
    ERROR = "ERROR"


class AuditStep(str, Enum):
    EXTRACCION_PDF = "EXTRACCION_PDF"
    VALIDACION_DOCUMENTAL = "VALIDACION_DOCUMENTAL"
    REVISION_USUARIO = "REVISION_USUARIO"
    EVALUACION_JURIDICA = "EVALUACION_JURIDICA"
    PROYECCION_ESCENARIO = "PROYECCION_ESCENARIO"
    LIQUIDACION_PENSIONAL = "LIQUIDACION_PENSIONAL"
    EXPORTACION_BORRADO = "EXPORTACION_BORRADO"


class EventCode(str, Enum):
    PDF_CARGADO = "PDF_CARGADO"
    PDF_FORMATO_NO_RECONOCIDO = "PDF_FORMATO_NO_RECONOCIDO"
    PDF_SIN_TEXTO_OCR_LOCAL = "PDF_SIN_TEXTO_OCR_LOCAL"
    PDF_VACIO = "PDF_VACIO"
    PDF_PROTEGIDO_CLAVE = "PDF_PROTEGIDO_CLAVE"
    PDF_CORRUPTO = "PDF_CORRUPTO"
    IBC_AMBIGUO = "IBC_AMBIGUO"
    COBERTURA_PARCIAL_INCIERTA = "COBERTURA_PARCIAL_INCIERTA"
    SIMULTANEIDAD_DETECTADA = "SIMULTANEIDAD_DETECTADA"
    DISCREPANCIA_RESUMEN_DETALLE = "DISCREPANCIA_RESUMEN_DETALLE"
    IPC_FALTANTE = "IPC_FALTANTE"
    SMLMV_FALTANTE = "SMLMV_FALTANTE"
    CORTE_REQUIERE_VALIDACION = "CORTE_REQUIERE_VALIDACION"
    TRANSICION_EVIDENCIA_SUFICIENTE = "TRANSICION_EVIDENCIA_SUFICIENTE"
    TRANSICION_NO_CUMPLE = "TRANSICION_NO_CUMPLE"
    TRANSICION_INFO_INSUFICIENTE = "TRANSICION_INFO_INSUFICIENTE"
    TRANSICION_CORTE_FUTURO = "TRANSICION_CORTE_FUTURO"
    IBL_INSUFICIENTE_DATOS_SALARIALES = "IBL_INSUFICIENTE_DATOS_SALARIALES"
    DEFICIT_SEMANAS_HORIZONTE = "DEFICIT_SEMANAS_HORIZONTE"
    HORIZONTE_HISTORICO_SUPERADO = "HORIZONTE_HISTORICO_SUPERADO"
    SIMULACION_COMPLETADA = "SIMULACION_COMPLETADA"
    SESION_BORRADA = "SESION_BORRADA"


@dataclass(frozen=True)
class TechnicalLogEntry:
    """Log entry without any personal or financial information."""

    timestamp_iso: str
    execution_id: str
    step: AuditStep
    component: str
    duration_ms: float
    severity: AuditSeverity
    event_code: EventCode
    status: str  # "INICIADO", "COMPLETADO", "ADVERTENCIA", "BLOQUEADO", "ERROR"
    technical_cause: str
    action_required: str

    def to_log_line(self) -> str:
        return (
            f"[{self.timestamp_iso}] [{self.severity.value}] [{self.execution_id[:8]}] "
            f"[{self.step.value}] [{self.event_code.value}] Status: {self.status} "
            f"({self.duration_ms:.1f}ms) - {self.technical_cause} | Acción: {self.action_required}"
        )


@dataclass
class PageExtractionAudit:
    page_number: int
    method: str  # "TEXTO_DIRECTO" | "OCR_LOCAL"
    text_length: int
    fragments_detected: int
    uninterpreted_lines: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass
class DataFieldAudit:
    field_name: str
    raw_text: str
    parsed_value: Any
    unit: str
    provenance: str
    validation_status: (
        str  # "VERIFICADO", "PENDIENTE_REVISION", "AMBIGUO", "INCORRECTO"
    )
    explanation: str = ""


@dataclass
class UserCorrectionAudit:
    field_name: str
    original_value: Any
    corrected_value: Any
    reason: str
    provenance: str
    timestamp_iso: str
    invalidated_evaluations: list[str] = field(default_factory=list)


@dataclass
class ScenarioCalculationAudit:
    scenario_id: str
    scenario_name: str
    fixed_horizon_date: str
    legal_retirement_age: int
    inputs: dict[str, Any]
    generated_future_periods_count: int
    weeks_breakdown: dict[str, float]
    effective_contributions_selected: list[dict[str, Any]]
    ibl_method_chosen: str
    ibl_final: float | None
    smlmv_ref: float
    s_factor: float | None
    replacement_rate_initial_pct: float | None
    additional_weeks_blocks: int | None
    replacement_rate_final_pct: float | None
    gross_pension: float | None
    limit_applied: str
    health_discount_pct: float | None
    health_discount_amount: float | None
    fsp_discount_pct: float | None
    fsp_discount_amount: float | None
    net_pension_after_discounts: float | None
    real_purchasing_power_cop: float | None
    smlmv_multiples: float | None
    is_blocked: bool
    blocking_reason: str | None
    step_by_step_operations: list[str]


@dataclass
class DocumentAuditRecord:
    execution_id: str
    schema_version: str = "2.0.0"
    created_at_iso: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    document_sha256: str = ""
    total_pages: int = 0
    pages_processed: int = 0
    pages_audit: list[PageExtractionAudit] = field(default_factory=list)
    extraction_status: str = (
        "COMPLETA"  # "COMPLETA", "ADVERTENCIA", "INCOMPLETA", "FORMATO_DESCONOCIDO"
    )
    detected_fields: list[DataFieldAudit] = field(default_factory=list)
    user_corrections: list[UserCorrectionAudit] = field(default_factory=list)
    documentary_discrepancies: list[str] = field(default_factory=list)
    transition_audit: dict[str, Any] = field(default_factory=dict)
    scenarios_audit: list[ScenarioCalculationAudit] = field(default_factory=list)
    sensitive_save_enabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "schema_version": self.schema_version,
            "created_at_iso": self.created_at_iso,
            "document_sha256": self.document_sha256,
            "total_pages": self.total_pages,
            "pages_processed": self.pages_processed,
            "pages_audit": [p.__dict__ for p in self.pages_audit],
            "extraction_status": self.extraction_status,
            "detected_fields": [f.__dict__ for f in self.detected_fields],
            "user_corrections": [c.__dict__ for c in self.user_corrections],
            "documentary_discrepancies": self.documentary_discrepancies,
            "transition_audit": self.transition_audit,
            "scenarios_audit": [s.__dict__ for s in self.scenarios_audit],
            "sensitive_save_enabled": self.sensitive_save_enabled,
        }
