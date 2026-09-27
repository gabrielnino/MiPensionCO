"""FastAPI Web Application & Local API for MiPensiónCO.

Runs exclusively on local loopback (127.0.0.1).
Zero external telemetry or cloud communication.
"""

import uuid
from datetime import date
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

from src.audit.models import AuditSeverity, AuditStep, EventCode
from src.audit.service import AuditService
from src.domain.models import (
    AffiliationStatus,
    CotizacionRecord,
    EscenarioConfig,
    HistoriaLaboral,
    ProvenanceType,
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


class HistoriaLaboralDTO(BaseModel):
    cedula_enmascarada: str = "ANON-XXXXX"
    nombre_enmascarado: str = ""
    fecha_nacimiento: str | None = None
    sexo: str | None = None  # "FEMENINO" | "MASCULINO"
    fecha_afiliacion_colpensiones: str | None = None
    fecha_primera_cotizacion: str | None = None
    fecha_expedicion_reporte: str | None = None
    fecha_actualizacion_reporte: str | None = None
    estado_afiliacion: str = "ACTIVO"
    semanas_resumen_colpensiones: float = 0.0
    semanas_alto_riesgo: float = 0.0
    tiempos_publicos: float = 0.0
    es_caso_especial: bool = False
    detalle_caso_especial: str = ""
    periodos_desconocidos_o_faltantes: bool = False
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


def dto_to_domain(dto: HistoriaLaboralDTO) -> HistoriaLaboral:
    """Converts API DTO into strongly typed domain model."""
    sexo_enum = None
    if dto.sexo:
        val = dto.sexo.upper()
        if val in ("FEMENINO", "MUJER", "F"):
            sexo_enum = SexCategory.FEMENINO
        elif val in ("MASCULINO", "HOMBRE", "M"):
            sexo_enum = SexCategory.MASCULINO

    estado_enum = AffiliationStatus.ACTIVO
    if dto.estado_afiliacion:
        st = dto.estado_afiliacion.upper()
        if "PENSIONADO" in st:
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

    return HistoriaLaboral(
        cedula_enmascarada=dto.cedula_enmascarada,
        nombre_enmascarado=dto.nombre_enmascarado,
        fecha_nacimiento=f_nac,
        sexo=sexo_enum,
        fecha_afiliacion_colpensiones=f_afil,
        fecha_primera_cotizacion=f_prim,
        fecha_expedicion_reporte=f_exp,
        fecha_actualizacion_reporte=f_act,
        estado_afiliacion=estado_enum,
        semanas_resumen_colpensiones=Decimal(str(dto.semanas_resumen_colpensiones)),
        semanas_alto_riesgo=Decimal(str(dto.semanas_alto_riesgo)),
        tiempos_publicos=Decimal(str(dto.tiempos_publicos)),
        es_caso_especial=dto.es_caso_especial,
        detalle_caso_especial=dto.detalle_caso_especial,
        registros=records,
        periodos_desconocidos_o_faltantes=dto.periodos_desconocidos_o_faltantes,
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
    return JSONResponse(
        content={
            "success": True,
            "report": {
                "execution_id": report.execution_id or exec_id,
                "pages_processed": report.pages_processed,
                "records_extracted": report.records_extracted,
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
                "estado_afiliacion": historia.estado_afiliacion.value,
                "semanas_resumen_colpensiones": float(
                    historia.semanas_resumen_colpensiones
                ),
                "semanas_alto_riesgo": float(historia.semanas_alto_riesgo),
                "tiempos_publicos": float(historia.tiempos_publicos),
                "es_caso_especial": historia.es_caso_especial,
                "detalle_caso_especial": historia.detalle_caso_especial,
                "periodos_desconocidos_o_faltantes": historia.periodos_desconocidos_o_faltantes,
                "registros": records_data,
            },
        }
    )


@app.post("/api/evaluate-transition")
async def evaluate_transition_endpoint(
    historia_dto: HistoriaLaboralDTO,
) -> JSONResponse:
    """Evaluates transition regime under Ley 2381 Art. 75 and C-264/2026."""
    historia = dto_to_domain(historia_dto)
    evaluation = PensionEngine.evaluate_transition(
        historia,
        as_of_date=date(2026, 9, 27),
        cutoff_date=TRANSITION_CUTOFF_DATE_C264,
    )
    return JSONResponse(content=evaluation.to_dict())


@app.post("/api/simulate")
async def simulate_endpoint(req: SimulateRequestDTO) -> JSONResponse:
    """Executes multi-scenario pension simulation strictly up to legal retirement age."""
    historia = dto_to_domain(req.historia)

    # First evaluate transition
    evaluation = PensionEngine.evaluate_transition(
        historia,
        as_of_date=date(2026, 9, 27),
        cutoff_date=TRANSITION_CUTOFF_DATE_C264,
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
    audit = AuditService.get_or_create_audit(execution_id)
    return JSONResponse(content=audit.to_dict())


@app.post("/api/audit/{execution_id}/save-local")
async def save_audit_local_endpoint(
    execution_id: str,
    enable_sensitive_save: bool = True,
) -> JSONResponse:
    """Saves complete audit record to local disk with user consent."""
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


@app.post("/api/reset-session")
async def reset_session(execution_id: str | None = None) -> JSONResponse:
    """Wipes in-memory session data and removes disk audit files."""
    AuditService.purge_session(execution_id=execution_id, purge_disk=True)
    if execution_id:
        AuditService.log_technical(
            execution_id,
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
            "status": "SESSION_CLEARED",
            "message": "Datos de sesión y auditoría borrados con éxito.",
        }
    )
