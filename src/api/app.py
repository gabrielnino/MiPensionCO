"""FastAPI Web Application & Local API for MiPensiónCO.

Runs exclusively on local loopback (127.0.0.1).
Zero external telemetry or cloud communication.
"""

import re
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
)
from pydantic import BaseModel

from src.audit.models import (
    AuditSeverity,
    AuditStep,
    EventCode,
    UserCorrectionAudit,
)
from src.audit.service import AuditService

EXEC_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]+$")


def validate_execution_id(execution_id: str) -> None:
    """Validates execution ID to prevent path traversal or malformed requests."""
    if (
        not execution_id
        or not EXEC_ID_REGEX.match(execution_id)
        or ".." in execution_id
    ):
        raise HTTPException(
            status_code=400,
            detail="Identificador de ejecución inválido.",
        )


from src.domain.models import (
    AffiliationStatus,
    CotizacionRecord,
    EscenarioConfig,
    HistoriaLaboral,
    ProvenanceType,
    ResumenEmpleadorRecord,
    SexCategory,
)
from src.domain.pension_engine import TRANSITION_CUTOFF_DATE_C264, PensionEngine
from src.economic.ipc import IPC_SERIES_BASE_2018
from src.economic.smlmv import HISTORICAL_SMLMV
from src.legal.catalog import LegalCatalog
from src.parser.pdf_reader import ColpensionesPDFReader

app = FastAPI(
    title="MiPensiónCO - Simulador Pensional Ordinario Local",
    description="Simulador de pensión de vejez para afiliados a Colpensiones con régimen de transición (Ley 100 de 1993)",
    version="1.0.0",
)

# CORS restricted strictly to localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)


# Pydantic DTOs for API requests & responses
class CotizacionRecordDTO(BaseModel):
    periodo_inicio: str
    periodo_fin: str
    dias_reportados: int
    dias_cotizados: int
    ibc: float
    aportante: str
    nit: str = ""
    novedad: str = ""
    observaciones: str = ""
    fecha_pago: str | None = None
    origen: str = "PDF"
    pagina: int = 1
    fila: int = 1


class ResumenEmpleadorRecordDTO(BaseModel):
    nit: str = ""
    nombre_aportante: str = ""
    periodo_inicio: str
    periodo_fin: str
    ultimo_salario: float = 0.0
    ultimo_salario_exacto: str = "0"
    semanas: float = 0.0
    licencias: float = 0.0
    simultaneidad: float = 0.0
    total_semanas: float = 0.0
    pagina: int = 1
    fila: int = 1
    source_fragment_ids: list[str] = []


class HistoriaLaboralDTO(BaseModel):
    cedula_enmascarada: str = "ANON-XXXXX"
    nombre_enmascarado: str = ""
    fecha_nacimiento: str | None = None
    sexo: str | None = None  # "FEMENINO" | "MASCULINO"
    fecha_afiliacion_colpensiones: str | None = None
    fecha_primera_cotizacion: str | None = None
    fecha_expedicion_reporte: str | None = None
    fecha_actualizacion_reporte: str | None = None
    ultimo_periodo_cotizado: str | None = None
    estado_afiliacion: str = "DESCONOCIDO"
    semanas_resumen_colpensiones: float = 0.0
    semanas_alto_riesgo: float | None = None
    tiempos_publicos: float = 0.0
    es_caso_especial: bool = False
    detalle_caso_especial: str = ""
    periodos_desconocidos_o_faltantes: bool = False
    aportes_posteriores_estado: str = "DESCONOCIDO"
    resumen_empleadores: list[ResumenEmpleadorRecordDTO] = []
    registros: list[CotizacionRecordDTO] = []


class EscenarioInputDTO(BaseModel):
    escenario_id: str
    nombre: str
    ibc_futuro_inicial: float
    fecha_inicio_ibc: str
    crecimiento_anual_nominal: float = 0.05
    periodos_sin_aporte: list[list[str]] = []  # [["YYYY-MM-DD", "YYYY-MM-DD"]]
    supuesto_inflacion: float = 0.040
    supuesto_crecimiento_smlmv: float = 0.055


class SimulateRequestDTO(BaseModel):
    historia: HistoriaLaboralDTO
    escenarios: list[EscenarioInputDTO]
    execution_id: str | None = None


class UserCorrectionDTO(BaseModel):
    execution_id: str
    target_field: str
    original_value: Any = None
    corrected_value: Any
    reason: str
    provenance: str = "DECLARACION_USUARIO"


def dto_to_domain(dto: HistoriaLaboralDTO) -> HistoriaLaboral:
    """Converts API DTO into strongly typed domain model."""
    sexo_enum = None
    if dto.sexo:
        val = dto.sexo.upper()
        if val in ("FEMENINO", "MUJER", "F"):
            sexo_enum = SexCategory.FEMENINO
        elif val in ("MASCULINO", "HOMBRE", "M"):
            sexo_enum = SexCategory.MASCULINO

    estado_enum = AffiliationStatus.DESCONOCIDO
    if dto.estado_afiliacion:
        st = dto.estado_afiliacion.upper()
        if "ACTIVO" in st:
            estado_enum = AffiliationStatus.ACTIVO
        elif "PENSIONADO" in st:
            estado_enum = AffiliationStatus.PENSIONADO
        elif "INACTIVO" in st:
            estado_enum = AffiliationStatus.INACTIVO

    records: list[CotizacionRecord] = []
    for r in dto.registros:
        try:
            p_ini = date.fromisoformat(r.periodo_inicio)
            p_fin = date.fromisoformat(r.periodo_fin)
            p_pago = date.fromisoformat(r.fecha_pago) if r.fecha_pago else None
        except ValueError:
            continue

        orig_enum = ProvenanceType.PDF
        if r.origen == "DECLARACION_USUARIO":
            orig_enum = ProvenanceType.DECLARACION_USUARIO
        elif r.origen == "SUPUESTO":
            orig_enum = ProvenanceType.SUPUESTO

        records.append(
            CotizacionRecord(
                periodo_inicio=p_ini,
                periodo_fin=p_fin,
                dias_reportados=r.dias_reportados,
                dias_cotizados=r.dias_cotizados,
                ibc=Decimal(str(r.ibc)),
                aportante=r.aportante,
                nit=r.nit,
                novedad=r.novedad,
                observaciones=r.observaciones,
                fecha_pago=p_pago,
                origen=orig_enum,
                pagina=r.pagina,
                fila=r.fila,
            )
        )

    resumen_list: list[ResumenEmpleadorRecord] = []
    for re_dto in dto.resumen_empleadores:
        try:
            r_ini = date.fromisoformat(re_dto.periodo_inicio)
            r_fin = date.fromisoformat(re_dto.periodo_fin)
        except ValueError:
            continue
        resumen_list.append(
            ResumenEmpleadorRecord(
                nit=re_dto.nit,
                nombre_aportante=re_dto.nombre_aportante,
                periodo_inicio=r_ini,
                periodo_fin=r_fin,
                ultimo_salario=Decimal(str(re_dto.ultimo_salario)),
                semanas=Decimal(str(re_dto.semanas)),
                licencias=Decimal(str(re_dto.licencias)),
                simultaneidad=Decimal(str(re_dto.simultaneidad)),
                total_semanas=Decimal(str(re_dto.total_semanas)),
                pagina=re_dto.pagina,
                fila=re_dto.fila,
                source_fragment_ids=tuple(re_dto.source_fragment_ids),
            )
        )

    f_nac = date.fromisoformat(dto.fecha_nacimiento) if dto.fecha_nacimiento else None
    f_afil = (
        date.fromisoformat(dto.fecha_afiliacion_colpensiones)
        if dto.fecha_afiliacion_colpensiones
        else None
    )
    f_prim = (
        date.fromisoformat(dto.fecha_primera_cotizacion)
        if dto.fecha_primera_cotizacion
        else None
    )
    f_exp = (
        date.fromisoformat(dto.fecha_expedicion_reporte)
        if dto.fecha_expedicion_reporte
        else None
    )
    f_act = (
        date.fromisoformat(dto.fecha_actualizacion_reporte)
        if dto.fecha_actualizacion_reporte
        else None
    )
    u_per = (
        date.fromisoformat(dto.ultimo_periodo_cotizado)
        if dto.ultimo_periodo_cotizado
        else None
    )

    ar_dec = (
        Decimal(str(dto.semanas_alto_riesgo))
        if dto.semanas_alto_riesgo is not None
        else None
    )

    return HistoriaLaboral(
        cedula_enmascarada=dto.cedula_enmascarada,
        nombre_enmascarado=dto.nombre_enmascarado,
        fecha_nacimiento=f_nac,
        sexo=sexo_enum,
        fecha_afiliacion_colpensiones=f_afil,
        fecha_primera_cotizacion=f_prim,
        fecha_expedicion_reporte=f_exp,
        fecha_actualizacion_reporte=f_act,
        ultimo_periodo_cotizado=u_per,
        estado_afiliacion=estado_enum,
        semanas_resumen_colpensiones=Decimal(str(dto.semanas_resumen_colpensiones)),
        semanas_alto_riesgo=ar_dec,
        tiempos_publicos=Decimal(str(dto.tiempos_publicos)),
        es_caso_especial=dto.es_caso_especial,
        detalle_caso_especial=dto.detalle_caso_especial,
        resumen_empleadores=resumen_list,
        registros=records,
        periodos_desconocidos_o_faltantes=dto.periodos_desconocidos_o_faltantes,
        aportes_posteriores_estado=dto.aportes_posteriores_estado,
    )


# --- Endpoints ---


@app.get("/", response_class=HTMLResponse)
async def serve_index() -> Any:
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse(
            "<h1>MiPensiónCO Backend Activo</h1><p>Archivo static/index.html en construcción.</p>"
        )
    return FileResponse(index_file)


@app.post("/api/upload")
async def upload_pdf(
    file: UploadFile = File(...),  # noqa: B008
    password: str | None = Form(None),
) -> JSONResponse:
    """Processes labor history PDF strictly in local memory."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="El archivo cargado debe ser un documento PDF."
        )

    contents = await file.read()
    exec_id = str(uuid.uuid4())
    historia, report = ColpensionesPDFReader.extract_from_bytes(
        contents, password=password, execution_id=exec_id
    )

    if report.requires_password:
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "requires_password": True,
                "execution_id": exec_id,
                "error_message": report.error_message
                or "El PDF está protegido con contraseña.",
            },
        )

    if not report.success or historia is None:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "execution_id": exec_id,
                "error_message": report.error_message
                or "No fue posible extraer la información del PDF.",
            },
        )

    # Convert to JSON serializable response
    records_data = [r.to_dict() for r in historia.registros]
    resumen_data = [r.to_dict() for r in historia.resumen_empleadores]

    audit = AuditService.get_or_create_audit(exec_id)
    field_statuses = {}
    for f in audit.detected_fields:
        field_statuses[f.field_name] = {
            "status": f.validation_status,
            "raw_text": f.raw_text,
            "parsed_value": f.parsed_value,
            "source_fragments": f.source_fragment_ids,
            "explanation": f.explanation,
        }

    return JSONResponse(
        content={
            "success": True,
            "report": {
                "execution_id": report.execution_id or exec_id,
                "pages_processed": report.pages_processed,
                "records_extracted": report.records_extracted,
                "summary_records_extracted": len(resumen_data),
                "warnings": report.warnings,
            },
            "data": {
                "cedula_enmascarada": historia.cedula_enmascarada,
                "nombre_enmascarado": historia.nombre_enmascarado,
                "fecha_nacimiento": historia.fecha_nacimiento.isoformat()
                if historia.fecha_nacimiento
                else None,
                "sexo": historia.sexo.value if historia.sexo else None,
                "fecha_afiliacion_colpensiones": historia.fecha_afiliacion_colpensiones.isoformat()
                if historia.fecha_afiliacion_colpensiones
                else None,
                "fecha_primera_cotizacion": historia.fecha_primera_cotizacion.isoformat()
                if historia.fecha_primera_cotizacion
                else None,
                "fecha_expedicion_reporte": historia.fecha_expedicion_reporte.isoformat()
                if historia.fecha_expedicion_reporte
                else None,
                "fecha_actualizacion_reporte": historia.fecha_actualizacion_reporte.isoformat()
                if historia.fecha_actualizacion_reporte
                else None,
                "ultimo_periodo_cotizado": historia.ultimo_periodo_cotizado.isoformat()
                if historia.ultimo_periodo_cotizado
                else None,
                "estado_afiliacion": historia.estado_afiliacion.value,
                "semanas_resumen_colpensiones": float(
                    historia.semanas_resumen_colpensiones
                ),
                "semanas_alto_riesgo": float(historia.semanas_alto_riesgo)
                if historia.semanas_alto_riesgo is not None
                else None,
                "tiempos_publicos": float(historia.tiempos_publicos),
                "es_caso_especial": historia.es_caso_especial,
                "detalle_caso_especial": historia.detalle_caso_especial,
                "periodos_desconocidos_o_faltantes": historia.periodos_desconocidos_o_faltantes,
                "aportes_posteriores_estado": historia.aportes_posteriores_estado,
                "resumen_empleadores": resumen_data,
                "registros": records_data,
                "field_statuses": field_statuses,
            },
        }
    )


@app.post("/api/evaluate-transition")
async def evaluate_transition_endpoint(
    historia_dto: HistoriaLaboralDTO,
    execution_id: str | None = None,
) -> JSONResponse:
    """Evaluates transition regime under Ley 2381 Art. 75 and C-264/2026."""
    if execution_id:
        validate_execution_id(execution_id)
    historia = dto_to_domain(historia_dto)
    evaluation = PensionEngine.evaluate_transition(
        historia,
        as_of_date=date(2026, 9, 27),
        cutoff_date=TRANSITION_CUTOFF_DATE_C264,
        execution_id=execution_id,
    )
    return JSONResponse(content=evaluation.to_dict())


@app.post("/api/audit/correction")
async def add_user_correction_endpoint(dto: UserCorrectionDTO) -> JSONResponse:
    """Registers verified user manual correction in audit trail."""
    validate_execution_id(dto.execution_id)
    audit = AuditService.get_or_create_audit(dto.execution_id)
    corr = UserCorrectionAudit(
        field_name=dto.target_field,
        original_value=dto.original_value,
        corrected_value=dto.corrected_value,
        reason=dto.reason,
        provenance="DECLARACION_USUARIO",
        timestamp_iso=datetime.now(timezone.utc).isoformat(),
        order=len(audit.user_corrections) + 1,
        invalidated_evaluations=["transition_evaluation", "scenario_simulations"],
    )
    audit.user_corrections.append(corr)
    return JSONResponse(content={"success": True, "correction": corr.__dict__})


@app.post("/api/simulate")
async def simulate_endpoint(req: SimulateRequestDTO) -> JSONResponse:
    """Executes multi-scenario pension simulation strictly up to legal retirement age."""
    if req.execution_id:
        validate_execution_id(req.execution_id)

    historia = dto_to_domain(req.historia)

    # First evaluate transition and record in audit
    evaluation = PensionEngine.evaluate_transition(
        historia,
        as_of_date=date(2026, 9, 27),
        cutoff_date=TRANSITION_CUTOFF_DATE_C264,
        execution_id=req.execution_id,
    )

    if not evaluation.permite_continuar_simulacion:
        return JSONResponse(
            status_code=400,
            content={
                "transition_evaluation": evaluation.to_dict(),
                "error": "No cumple los requisitos para proyectar bajo el régimen de transición de la Ley 100 de 1993.",
                "results": [],
            },
        )

    engine = PensionEngine()
    results: list[dict[str, Any]] = []

    for esc_dto in req.escenarios:
        pausas = []
        for p in esc_dto.periodos_sin_aporte:
            if len(p) == 2:
                try:
                    pausas.append((date.fromisoformat(p[0]), date.fromisoformat(p[1])))
                except ValueError:
                    pass

        try:
            f_ini_ibc = date.fromisoformat(esc_dto.fecha_inicio_ibc)
        except ValueError:
            f_ini_ibc = date(2026, 1, 1)

        esc = EscenarioConfig(
            escenario_id=esc_dto.escenario_id,
            nombre=esc_dto.nombre,
            ibc_futuro_inicial=Decimal(str(esc_dto.ibc_futuro_inicial)),
            fecha_inicio_ibc=f_ini_ibc,
            crecimiento_anual_nominal=Decimal(str(esc_dto.crecimiento_anual_nominal)),
            periodos_sin_aporte=pausas,
            supuesto_inflacion=Decimal(str(esc_dto.supuesto_inflacion)),
            supuesto_crecimiento_smlmv=Decimal(str(esc_dto.supuesto_crecimiento_smlmv)),
        )

        sim_res = engine.simulate_scenario(
            historia, esc, as_of_date=date(2026, 9, 27), execution_id=req.execution_id
        )
        results.append(sim_res.to_dict())

    return JSONResponse(
        content={
            "transition_evaluation": evaluation.to_dict(),
            "execution_id": req.execution_id,
            "results": results,
        }
    )


@app.get("/api/audit/{execution_id}")
async def get_audit_endpoint(execution_id: str) -> JSONResponse:
    """Returns detailed in-memory audit record for a given execution ID."""
    validate_execution_id(execution_id)
    audit = AuditService.get_or_create_audit(execution_id)
    return JSONResponse(content=audit.to_dict())


@app.get("/api/audit/{execution_id}/export")
async def export_audit_endpoint(execution_id: str) -> JSONResponse:
    """Returns complete downloadable audit JSON."""
    validate_execution_id(execution_id)
    audit = AuditService.get_or_create_audit(execution_id)
    return JSONResponse(
        content=audit.to_dict(),
        headers={
            "Content-Disposition": f'attachment; filename="auditoria_{execution_id}.json"'
        },
    )


@app.post("/api/audit/{execution_id}/save-local")
async def save_audit_local_endpoint(
    execution_id: str,
    enable_sensitive_save: bool = True,
) -> JSONResponse:
    """Saves complete audit record to local disk with user consent."""
    validate_execution_id(execution_id)
    saved_path = AuditService.save_audit_locally(
        execution_id, enable_sensitive_save=enable_sensitive_save
    )
    if not saved_path:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "No se pudo guardar la auditoría local o está deshabilitada.",
            },
        )
    return JSONResponse(
        content={
            "success": True,
            "message": f"Auditoría guardada exitosamente en {saved_path.name}",
            "file_path": str(saved_path),
        }
    )


@app.get("/api/audit/{execution_id}/report.md")
async def get_audit_markdown_endpoint(execution_id: str) -> PlainTextResponse:
    """Returns Markdown diagnostic report for human review."""
    validate_execution_id(execution_id)
    report_text = AuditService.generate_markdown_report(execution_id)
    return PlainTextResponse(content=report_text, media_type="text/markdown")


@app.get("/api/catalog")
async def get_legal_catalog() -> JSONResponse:
    """Returns independent legal rules catalog."""
    rules = [r.to_dict() for r in LegalCatalog.list_all_rules()]
    return JSONResponse(content={"baseline_date": "2026-09-27", "rules": rules})


@app.get("/api/economic-data")
async def get_economic_data() -> JSONResponse:
    """Returns official historical SMLMV and DANE IPC indices."""
    smlmv_list = [
        {
            "year": rec.year,
            "monthly_amount": float(rec.monthly_amount),
            "decree": rec.decree_reference,
            "source_url": rec.official_source_url,
        }
        for rec in sorted(HISTORICAL_SMLMV.values(), key=lambda x: x.year)
    ]

    ipc_list = [
        {"year": k[0], "month": k[1], "index": float(v)}
        for k, v in sorted(IPC_SERIES_BASE_2018.items())
    ]

    return JSONResponse(content={"smlmv": smlmv_list, "ipc": ipc_list})


class ResetSessionDTO(BaseModel):
    execution_id: str | None = None
    delete_persisted_audit: bool = True


@app.post("/api/reset-session")
async def reset_session(
    dto: ResetSessionDTO | None = None,
    execution_id: str | None = None,
    delete_persisted_audit: bool = True,
) -> JSONResponse:
    """Wipes in-memory session data and removes disk audit files."""
    target_id = dto.execution_id if dto and dto.execution_id else execution_id
    purge_disk = dto.delete_persisted_audit if dto else delete_persisted_audit
    if target_id:
        validate_execution_id(target_id)
    AuditService.purge_session(execution_id=target_id, purge_disk=purge_disk)
    if target_id:
        AuditService.log_technical(
            target_id,
            AuditStep.EXPORTACION_BORRADO,
            "AuditService",
            0.0,
            AuditSeverity.INFO,
            EventCode.SESION_BORRADA,
            "COMPLETADO",
            "Sesión y auditoría purgadas",
            "Ninguna",
        )
    return JSONResponse(
        content={
            "success": True,
            "status": "SESSION_CLEARED",
            "message": "Datos de sesión y auditoría borrados con éxito.",
        }
    )
