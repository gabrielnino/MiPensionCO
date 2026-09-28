"""TDD Test Suite for Stage 2 & Stage 3: PDF Review Form, Audit Trail, and Session Wipe.

Verifies Hallazgo 4, 5, 6, and 7 per AGENTS.md, TDD, and project specifications.
"""

from datetime import date
from decimal import Decimal

from starlette.testclient import TestClient

from src.api.app import app
from src.audit.service import AuditService
from src.domain.models import (
    CotizacionRecord,
    EscenarioConfig,
    HistoriaLaboral,
    ProvenanceType,
    SexCategory,
)
from src.domain.pension_engine import PensionEngine
from src.parser.pdf_reader import ColpensionesPDFReader
from src.parser.synthetic_generator import create_synthetic_colpensiones_pdf


# ---------------------------------------------------------------------------
# Hallazgo 4: Formato de fechas en texto español y recepción inequívoca
# ---------------------------------------------------------------------------
def test_hallazgo_4_spanish_date_normalization_roundtrip() -> None:
    """PDF with 'ACTUALIZADO A: 30 agosto 2025' must normalize to 2025-08-30,

    never October or wrong month, and pass exact date to engine.
    """
    client = TestClient(app)
    pdf_bytes = create_synthetic_colpensiones_pdf(
        fecha_actualizacion="30 agosto 2025",
        records_lines=[
            "01/01/2020 31/12/2024 1800 $ 3.000.000 EMPRESA TEST",
        ],
    )

    # 1. Extraction from bytes directly
    historia, report = ColpensionesPDFReader.extract_from_bytes(pdf_bytes)
    assert report.success is True
    assert historia is not None
    assert historia.fecha_actualizacion_reporte == date(2025, 8, 30), (
        f"Expected August 30, 2025, got {historia.fecha_actualizacion_reporte}"
    )

    # 2. Upload endpoint returns ISO string 2025-08-30
    resp = client.post(
        "/api/upload", files={"file": ("historia.pdf", pdf_bytes, "application/pdf")}
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["fecha_actualizacion_reporte"] == "2025-08-30"

    # 3. Engine simulation receives this date and does not invent retroactivity
    data["fecha_nacimiento"] = "1964-05-15"
    data["sexo"] = "MASCULINO"
    data["semanas_resumen_colpensiones"] = 1300.0

    sim_resp = client.post(
        f"/api/simulate?execution_id={resp.json()['report']['execution_id']}",
        json={
            "historia": data,
            "escenarios": [
                {
                    "escenario_id": "esc1",
                    "nombre": "Escenario Base",
                    "ibc_futuro_inicial": 3000000.0,
                    "fecha_inicio_ibc": "2025-09-01",
                    "crecimiento_anual_nominal": 0.05,
                    "inflacion_anual_esperada": 0.04,
                }
            ],
        },
    )
    assert sim_resp.status_code == 200
    sim_data = sim_resp.json()
    assert len(sim_data["results"]) == 1


# ---------------------------------------------------------------------------
# Hallazgo 5: Correcciones registradas con campos obligatorios y tabla dual
# ---------------------------------------------------------------------------
def test_hallazgo_5_form_corrections_linked_to_audit() -> None:
    """Modifications in review form must record field_name, original_value,

    corrected_value, reason, provenance, and timestamp in audit.
    User declared records must be explicitly marked as DECLARACION_USUARIO.
    """
    client = TestClient(app)
    exec_id = "test-h5-corr-audit"
    AuditService.get_or_create_audit(exec_id)

    # Register field correction via API
    corr_payload = {
        "execution_id": exec_id,
        "target_field": "semanas_resumen_colpensiones",
        "original_value": 1200.0,
        "corrected_value": 1300.0,
        "reason": "Corrección con base en certificado empleador anexo",
        "provenance": "DECLARACION_USUARIO",
    }
    resp = client.post("/api/audit/correction", json=corr_payload)
    assert resp.status_code == 200

    audit = AuditService.get_or_create_audit(exec_id)
    assert len(audit.user_corrections) == 1
    c = audit.user_corrections[0]
    assert c.field_name == "semanas_resumen_colpensiones"
    assert c.original_value == 1200.0
    assert c.corrected_value == 1300.0
    assert c.reason == "Corrección con base en certificado empleador anexo"
    assert c.provenance == "DECLARACION_USUARIO"
    assert c.timestamp_iso is not None

    # Simulate with declared record
    declared_record = CotizacionRecord(
        periodo_inicio=date(2025, 1, 1),
        periodo_fin=date(2025, 6, 30),
        dias_reportados=180,
        dias_cotizados=180,
        ibc=Decimal(3500000),
        aportante="EMPRESA DECLARADA",
        origen=ProvenanceType.DECLARACION_USUARIO,
    )
    historia = HistoriaLaboral(
        cedula_enmascarada="ANON-H5",
        fecha_nacimiento=date(1964, 1, 1),
        sexo=SexCategory.MASCULINO,
        semanas_resumen_colpensiones=Decimal(1300),
        registros=[declared_record],
    )
    engine = PensionEngine()
    esc = EscenarioConfig("esc1", "Escenario", Decimal(3500000), date(2025, 7, 1))
    _ = engine.simulate_scenario(
        historia, esc, as_of_date=date(2025, 7, 1), execution_id=exec_id
    )

    # Audit breakdown must include declared weeks
    sc_audit = next(s for s in audit.scenarios_audit if s.scenario_id == "esc1")
    assert "declaradas" in sc_audit.weeks_breakdown
    assert sc_audit.weeks_breakdown["declaradas"] == str(Decimal("25.71"))


# ---------------------------------------------------------------------------
# Hallazgo 6: Auditoría de parámetros completos del escenario y pausas
# ---------------------------------------------------------------------------
def test_hallazgo_6_scenario_audit_inputs_pauses_and_string_decimals() -> None:
    """Audit must record all scenario inputs, pause/termination reason,

    economic assumptions, and exact string-serialized monetary decimals.
    """
    exec_id = "test-h6-scenario-audit"
    AuditService.get_or_create_audit(exec_id)
    engine = PensionEngine()

    # Scenario 1: Worker reaching legal retirement age in 2032
    recs_active = [
        CotizacionRecord(
            periodo_inicio=date(2005, 1, 1),
            periodo_fin=date(2025, 12, 31),
            dias_reportados=1050 * 7,
            dias_cotizados=1050 * 7,
            ibc=Decimal(3500000),
            aportante="EMPRESA ACTIVA",
        )
    ]
    historia_active = HistoriaLaboral(
        cedula_enmascarada="ANON-H6-ACT",
        fecha_nacimiento=date(1970, 5, 1),
        sexo=SexCategory.MASCULINO,
        semanas_resumen_colpensiones=Decimal(1050),
        registros=recs_active,
    )
    esc_active = EscenarioConfig(
        escenario_id="esc_active",
        nombre="Trabajador activo proyectado",
        ibc_futuro_inicial=Decimal(3500000),
        fecha_inicio_ibc=date(2026, 1, 1),
        crecimiento_anual_nominal=Decimal("0.05"),
        supuesto_inflacion=Decimal("0.04"),
        supuesto_crecimiento_smlmv=Decimal("0.055"),
    )
    res_active = engine.simulate_scenario(
        historia_active, esc_active, as_of_date=date(2026, 9, 27), execution_id=exec_id
    )
    assert res_active.cumple_semanas is True

    audit = AuditService.get_or_create_audit(exec_id)
    sc1 = next(s for s in audit.scenarios_audit if s.scenario_id == "esc_active")

    # Inputs must be complete
    assert sc1.inputs["ibc_futuro_nominal"] == "3500000"
    assert sc1.inputs["fecha_inicio_ibc"] == "2026-01-01"
    assert sc1.inputs["crecimiento_anual_nominal"] == "0.05"
    assert Decimal(sc1.inputs["semanas_proyectadas"]) > Decimal(0)

    # Pause/termination reason for reaching legal age
    assert "horizonte fijo" in sc1.inputs["motivo_terminacion_o_pausa_aportes"].lower()

    # Economic assumptions must be present
    assert "supuestos_economicos" in sc1.inputs
    assert sc1.inputs["supuestos_economicos"]["inflacion_anual_proyeccion"] == "0.04"
    assert sc1.inputs["supuestos_economicos"]["crecimiento_anual_smlmv"] == "0.055"

    # Monetary values must be serialized as strings, not floats
    assert isinstance(sc1.ibl_final, str)
    assert isinstance(sc1.gross_pension, str)
    assert isinstance(sc1.net_pension_after_discounts, str)
    assert isinstance(sc1.smlmv_ref, str)

    # Scenario 2: Worker who ALREADY exceeded legal age
    historia_past = HistoriaLaboral(
        cedula_enmascarada="ANON-H6-PAST",
        fecha_nacimiento=date(1955, 1, 1),
        sexo=SexCategory.MASCULINO,
        semanas_resumen_colpensiones=Decimal(1300),
        registros=recs_active,
    )
    esc_past = EscenarioConfig(
        escenario_id="esc_past",
        nombre="Trabajador con edad superada",
        ibc_futuro_inicial=Decimal(3500000),
        fecha_inicio_ibc=date(2026, 1, 1),
    )
    engine.simulate_scenario(
        historia_past, esc_past, as_of_date=date(2026, 9, 27), execution_id=exec_id
    )
    sc2 = next(s for s in audit.scenarios_audit if s.scenario_id == "esc_past")
    assert "superó" in sc2.inputs["motivo_terminacion_o_pausa_aportes"].lower()
    assert Decimal(sc2.inputs["semanas_proyectadas"]) == Decimal(0)


# ---------------------------------------------------------------------------
# Hallazgo 7: Distinción entre borrado de sesión (RAM) y borrado en disco
# ---------------------------------------------------------------------------
def test_hallazgo_7_session_reset_distinction_memory_vs_disk() -> None:
    """Resetting session clears memory and DOM. Deleting persisted disk audit

    must be an explicit option (delete_persisted_audit), default False.
    """
    client = TestClient(app)
    exec_id = "test-h7-wipe-distinction"

    # 1. Create audit and save to disk
    _ = AuditService.get_or_create_audit(exec_id)
    saved_path = AuditService.save_audit_locally(exec_id, enable_sensitive_save=True)
    assert saved_path is not None
    assert saved_path.exists()

    # 2. Reset session WITHOUT deleting persisted audit
    resp_soft = client.post(
        "/api/reset-session",
        json={"execution_id": exec_id, "delete_persisted_audit": False},
    )
    assert resp_soft.status_code == 200
    # In-memory audit is gone
    assert exec_id not in AuditService._active_audits
    # Disk file STILL EXISTS!
    assert saved_path.exists()

    # 3. Reset session WITH explicit deletion of persisted audit
    resp_hard = client.post(
        "/api/reset-session",
        json={"execution_id": exec_id, "delete_persisted_audit": True},
    )
    assert resp_hard.status_code == 200
    # Disk file is now purged!
    assert not saved_path.exists()
