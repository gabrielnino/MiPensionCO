"""Integration and API Endpoint tests for MiPensiónCO."""

import io

from starlette.testclient import TestClient

from src.api.app import app
from src.parser.synthetic_generator import create_synthetic_colpensiones_pdf

client = TestClient(app)


def test_api_index():
    response = client.get("/")
    assert response.status_code == 200


def test_api_legal_catalog():
    response = client.get("/api/catalog")
    assert response.status_code == 200
    data = response.json()
    assert "rules" in data
    assert len(data["rules"]) >= 14


def test_api_economic_data():
    response = client.get("/api/economic-data")
    assert response.status_code == 200
    data = response.json()
    assert "smlmv" in data
    assert "ipc" in data
    assert len(data["smlmv"]) > 20


def test_api_upload_pdf():
    pdf_bytes = create_synthetic_colpensiones_pdf(
        fecha_nacimiento="20/08/1970",
        sexo="FEMENINO",
        total_semanas="780.50",
    )
    files = {"file": ("historia_laboral.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post("/api/upload", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["semanas_resumen_colpensiones"] == 780.50
    assert data["data"]["sexo"] == "FEMENINO"


def test_api_upload_encrypted_pdf_prompt_password():
    pdf_bytes = create_synthetic_colpensiones_pdf(password="clave123")
    files = {"file": ("protegido.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    # Without password
    res1 = client.post("/api/upload", files=files)
    assert res1.status_code == 401
    assert res1.json()["requires_password"] is True

    # With password
    files2 = {"file": ("protegido.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    res2 = client.post("/api/upload", files=files2, data={"password": "clave123"})
    assert res2.status_code == 200
    assert res2.json()["success"] is True


def test_api_evaluate_transition_endpoint():
    payload = {
        "cedula_enmascarada": "123456",
        "sexo": "FEMENINO",
        "semanas_resumen_colpensiones": 760.0,
        "fecha_actualizacion_reporte": "2025-01-10",
        "registros": [],
    }
    response = client.post("/api/evaluate-transition", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "EVIDENCIA_SUFICIENTE_CUMPLIMIENTO"
    assert data["permite_continuar_simulacion"] is True


def test_api_simulate_endpoint():
    payload = {
        "historia": {
            "cedula_enmascarada": "123456",
            "fecha_nacimiento": "1970-08-20",
            "sexo": "FEMENINO",
            "semanas_resumen_colpensiones": 800.0,
            "fecha_actualizacion_reporte": "2025-01-10",
            "registros": [
                {
                    "periodo_inicio": "2024-01-01",
                    "periodo_fin": "2024-12-31",
                    "dias_reportados": 365,
                    "dias_cotizados": 365,
                    "ibc": 3000000.0,
                    "aportante": "EMPRESA A",
                }
            ],
        },
        "escenarios": [
            {
                "escenario_id": "esc_1",
                "nombre": "Escenario Base",
                "ibc_futuro_inicial": 3500000.0,
                "fecha_inicio_ibc": "2026-01-01",
                "crecimiento_anual_nominal": 0.05,
                "periodos_sin_aporte": [],
                "supuesto_inflacion": 0.04,
                "supuesto_crecimiento_smlmv": 0.055,
            }
        ],
    }
    response = client.post("/api/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 1
    assert data["results"][0]["edad_legal"] == 57


def test_api_reset_session():
    response = client.post("/api/reset-session")
    assert response.status_code == 200
    assert response.json()["status"] == "SESSION_CLEARED"


def test_api_audit_endpoints():
    pdf_bytes = create_synthetic_colpensiones_pdf(
        fecha_nacimiento="20/08/1970",
        sexo="FEMENINO",
        total_semanas="780.50",
    )
    files = {"file": ("historia_audit.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    res_upload = client.post("/api/upload", files=files)
    assert res_upload.status_code == 200
    exec_id = res_upload.json()["report"]["execution_id"]
    assert exec_id is not None

    # Simulate with execution_id
    payload = {
        "execution_id": exec_id,
        "historia": res_upload.json()["data"],
        "escenarios": [
            {
                "escenario_id": "esc_aud",
                "nombre": "Escenario Auditoría",
                "ibc_futuro_inicial": 3500000.0,
                "fecha_inicio_ibc": "2026-01-01",
                "crecimiento_anual_nominal": 0.05,
                "periodos_sin_aporte": [],
                "supuesto_inflacion": 0.04,
                "supuesto_crecimiento_smlmv": 0.055,
            }
        ],
    }
    res_sim = client.post("/api/simulate", json=payload)
    assert res_sim.status_code == 200

    # 1. GET /api/audit/{execution_id}
    res_audit = client.get(f"/api/audit/{exec_id}")
    assert res_audit.status_code == 200
    audit_data = res_audit.json()
    assert audit_data["execution_id"] == exec_id
    assert len(audit_data["pages_audit"]) >= 1
    assert len(audit_data["scenarios_audit"]) >= 1

    # 2. POST /api/audit/{execution_id}/save-local
    res_save = client.post(f"/api/audit/{exec_id}/save-local")
    assert res_save.status_code == 200
    assert res_save.json()["success"] is True

    # 3. GET /api/audit/{execution_id}/report.md
    res_md = client.get(f"/api/audit/{exec_id}/report.md")
    assert res_md.status_code == 200
    assert "Auditoría Detallada" in res_md.text

    # 4. POST /api/reset-session with execution_id
    res_purge = client.post(f"/api/reset-session?execution_id={exec_id}")
    assert res_purge.status_code == 200
