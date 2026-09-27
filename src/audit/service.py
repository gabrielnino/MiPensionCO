"""Audit Service for MiPensiónCO.

Manages:
1. Technical Log without PII in logs/technical_audit.log.
2. In-memory Calculation & Documentary Audit with optional local disk persistence
   under audit/ using atomic file writes.
"""

import json
import logging
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar

from src.audit.models import (
    AuditSeverity,
    AuditStep,
    DocumentAuditRecord,
    EventCode,
    ScenarioCalculationAudit,
    TechnicalLogEntry,
)

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR = BASE_DIR / "audit"

TECH_LOG_FILE = LOG_DIR / "technical_audit.log"


def atomic_write_json(file_path: Path, data: dict) -> None:  # type: ignore
    """Writes JSON atomically using a temporary swap file to prevent corruption."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", dir=file_path.parent, delete=False, encoding="utf-8"
    ) as tf:
        json.dump(data, tf, indent=2, ensure_ascii=False)
        temp_name = tf.name
    Path(temp_name).replace(file_path)


class AuditService:
    """Singleton service managing technical and documentary audits."""

    _active_audits: ClassVar[dict[str, DocumentAuditRecord]] = {}

    @classmethod
    def log_technical(
        cls,
        execution_id: str,
        step: AuditStep,
        component: str,
        duration_ms: float,
        severity: AuditSeverity,
        event_code: EventCode,
        status: str,
        technical_cause: str,
        action_required: str,
    ) -> None:
        """Appends a sanitized technical entry without any personal or financial PII.

        Filters out freeform user values, mesada/salary numbers, and names.
        """
        import re

        clean_cause = re.sub(r"\$[\s0-9.,]+", "[VALOR_PROTEGIDO]", technical_cause)
        clean_cause = re.sub(r"\b[0-9]{5,}\b", "[ID_PROTEGIDO]", clean_cause)
        clean_action = re.sub(r"\$[\s0-9.,]+", "[VALOR_PROTEGIDO]", action_required)
        clean_action = re.sub(r"\b[0-9]{5,}\b", "[ID_PROTEGIDO]", clean_action)

        entry = TechnicalLogEntry(
            timestamp_iso=datetime.now(timezone.utc).isoformat(),
            execution_id=execution_id,
            step=step,
            component=component,
            duration_ms=duration_ms,
            severity=severity,
            event_code=event_code,
            status=status,
            technical_cause=clean_cause,
            action_required=clean_action,
        )
        try:
            with open(TECH_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(entry.to_log_line() + "\n")
        except OSError as exc:
            logger.error("Error escribiendo en log técnico: %s", exc)

    @classmethod
    def get_or_create_audit(
        cls, execution_id: str | None = None
    ) -> DocumentAuditRecord:
        """Retrieves or initializes in-memory audit record for an execution."""
        if not execution_id or not re.match(r"^[a-zA-Z0-9_-]+$", execution_id):
            execution_id = str(uuid.uuid4())

        if execution_id not in cls._active_audits:
            cls._active_audits[execution_id] = DocumentAuditRecord(
                execution_id=execution_id
            )
        return cls._active_audits[execution_id]

    @classmethod
    def add_scenario_audit(
        cls, execution_id: str, scenario_audit: ScenarioCalculationAudit
    ) -> None:
        """Records scenario calculation audit in memory."""
        audit = cls.get_or_create_audit(execution_id)
        # Update or append scenario audit by scenario_id
        existing_idx = next(
            (
                idx
                for idx, s in enumerate(audit.scenarios_audit)
                if s.scenario_id == scenario_audit.scenario_id
            ),
            None,
        )
        if existing_idx is not None:
            audit.scenarios_audit[existing_idx] = scenario_audit
        else:
            audit.scenarios_audit.append(scenario_audit)

    @classmethod
    def save_audit_locally(
        cls, execution_id: str, enable_sensitive_save: bool = True
    ) -> Path | None:
        """Atomically saves full calculation and documentary audit to disk if enabled by user."""
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", execution_id):
            raise ValueError("Identificador de ejecución no válido.")

        if execution_id not in cls._active_audits:
            return None
        audit = cls._active_audits[execution_id]
        audit.sensitive_save_enabled = enable_sensitive_save

        if not enable_sensitive_save:
            return None

        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        file_path = AUDIT_DIR / f"audit_{execution_id}.json"
        atomic_write_json(file_path, audit.to_dict())
        return file_path

    @classmethod
    def purge_session(
        cls, execution_id: str | None = None, purge_disk: bool = False
    ) -> None:
        """Purges memory session and optionally deletes disk audit files if requested."""
        import re

        if execution_id:
            if not re.match(r"^[a-zA-Z0-9_-]+$", execution_id):
                raise ValueError("Identificador de ejecución no válido.")
            cls._active_audits.pop(execution_id, None)
            if purge_disk:
                target = AUDIT_DIR / f"audit_{execution_id}.json"
                if target.exists():
                    target.unlink()
        else:
            cls._active_audits.clear()
            if purge_disk and AUDIT_DIR.exists():
                for f in AUDIT_DIR.glob("audit_*.json"):
                    try:
                        f.unlink()
                    except OSError:
                        pass

    @classmethod
    def generate_markdown_report(cls, execution_id: str) -> str:
        """Generates a human-readable diagnostic report of the audit."""
        audit = cls.get_or_create_audit(execution_id)
        md = []
        md.append("# Auditoría Detallada de Simulación Pensional: MiPensiónCO")
        md.append(f"**Identificador de Ejecución:** `{audit.execution_id}`  ")
        md.append(f"**Fecha y Hora:** {audit.created_at_iso}  ")
        md.append(
            f"**Huella Digital del Documento (SHA256):** `{audit.document_sha256[:16]}...`  "
        )
        md.append(
            f"**Estado de Integridad de Extracción:** `{audit.extraction_status}`  "
        )
        md.append("")
        md.append("## 1. Extracción por Página")
        for p in audit.pages_audit:
            md.append(
                f"- **Página {p.page_number}:** Método `{p.method}` | Fragmentos: {p.fragments_detected} | Líneas sin interpretar: {len(p.uninterpreted_lines)}"
            )
        md.append("")
        md.append("## 2. Validación Documental y Discrepancias")
        if audit.documentary_discrepancies:
            for disc in audit.documentary_discrepancies:
                md.append(f"- ⚠️ {disc}")
        else:
            md.append("- No se detectaron inconsistencias documentales.")
        md.append("")
        md.append("## 3. Evaluación Jurídica de Transición")
        for k, v in audit.transition_audit.items():
            md.append(f"- **{k}:** {v}")
        md.append("")
        md.append("## 4. Escenarios y Liquidación")
        for s in audit.scenarios_audit:
            status = "BLOQUEADA" if s.is_blocked else "LIQUIDADA"
            md.append(f"### Escenario: {s.scenario_name} ({status})")
            if s.is_blocked:
                md.append(f"> **Causa de Bloqueo:** {s.blocking_reason}")
            else:
                md.append(
                    f"- **Horizonte Fijo:** {s.fixed_horizon_date} ({s.legal_retirement_age} años)"
                )
                ibl_str = f"${float(s.ibl_final):,.0f} COP" if s.ibl_final else "N/A"
                gross_str = (
                    f"${float(s.gross_pension):,.0f} COP" if s.gross_pension else "N/A"
                )
                salud_monto_str = (
                    f"${float(s.health_discount_amount):,.0f}"
                    if s.health_discount_amount
                    else "$0"
                )
                fsp_monto_str = (
                    f"${float(s.fsp_discount_amount):,.0f}"
                    if s.fsp_discount_amount
                    else "$0"
                )
                net_str = (
                    f"${float(s.net_pension_after_discounts):,.0f} COP"
                    if s.net_pension_after_discounts
                    else "N/A"
                )
                md.append(f"- **IBL Liquidado:** {ibl_str} ({s.ibl_method_chosen})")
                md.append(
                    f"- **Tasa de Reemplazo:** {s.replacement_rate_final_pct}% (Inicial: {s.replacement_rate_initial_pct}%)"
                )
                md.append(
                    f"- **Mesada Bruta:** {gross_str} | Límite: {s.limit_applied}"
                )
                md.append(
                    f"- **Descuentos:** Salud ({s.health_discount_pct}% = {salud_monto_str}) | FSP ({s.fsp_discount_pct}% = {fsp_monto_str})"
                )
                md.append(f"- **Valor Estimado tras Descuentos:** {net_str}")
            md.append("")
            md.append("#### Desglose de Operaciones Reales")
            for op in s.step_by_step_operations:
                md.append(f"1. {op}")
            md.append("")
        return "\n".join(md)
